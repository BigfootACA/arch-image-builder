import os
import io
import gzip
from logging import getLogger
from tempfile import mkstemp
from builder.disk.content import ImageContentBuilder
from builder.lib.config import ArchBuilderConfigError
from external.mkbootimg import main as mkbootimg
log = getLogger(__name__)


class AndroidBootBuilder(ImageContentBuilder):
	temps: list[str] = []

	def to_list(self, val: str | list[str] | None) -> list[str]:
		if type(val) is str: return [val]
		if type(val) is None: return []
		if type(val) is list[str]: return val
		raise TypeError("bad type for list")

	def get_input_file(self, name: str):
		ctx = self.builder.ctx
		if name.startswith("/"): return name
		in_root = os.path.join(ctx.get_rootfs(), name)
		in_out = os.path.join(ctx.get_output(), name)
		return in_root if os.path.exists(in_root) else in_out

	def parse_config(self, cfg: dict) -> list:
		ret: list[str] = []
		def add_option(key: str, file: bool = False):
			if key not in cfg: return
			val = str(cfg[key])
			key = "--" + key.replace("-", "_")
			if file: val = self.get_input_file(val)
			ret.extend([key, val])
		file_in = [
			"kernel", "ramdisk", "second", "dtb", "recovery-dtbo",
			"recovery-acpio", "vendor-ramdisk", "vendor-bootconfig",
		]
		fields = [
			"header-version", "cmdline", "vendor-cmdline", "base",
			"kernel-offset", "ramdisk-offset", "second-offset",
			"dtb-offset", "os-version", "os-patch-level", "tags-offset",
			"board", "pagesize", "header-version",
		]
		for arg in fields: add_option(arg)
		for arg in file_in: add_option(arg, True)
		return ret

	def resolve_kernel(self, files: list[str] | str) -> list[str]:
		ret: list[str] = []
		if files is None: return ret
		ctx = self.builder.ctx
		rootfs = ctx.get_rootfs()
		path: str = ctx.get("kernel.path", "")
		if path.startswith("/"): path = path[1:]
		for file in self.to_list(files):
			if file.startswith("/"): file = file[1:]
			ret.append(os.path.join(rootfs, path, file))
		return ret

	def merge_fp(self, files: list[str], fp: io.FileIO):
		for f in files:
			inp = self.get_input_file(f)
			with open(inp, "rb") as fi:
				fp.write(fi.read())
		fp.flush()

	def merge_files(self, files: list[str]):
		fd, file = mkstemp()
		with os.fdopen(fd, "wb") as fo:
			self.merge_fp(files, fo)
		return file

	def load_initramfs(self, cfg: dict):
		ctx = self.builder.ctx
		initramfs = self.resolve_kernel(ctx.get("kernel.initramfs"))
		if "ramdisk" in cfg: initramfs = self.to_list(cfg["ramdisk"])
		if len(initramfs) <= 0: return
		file = self.merge_files(initramfs)
		self.temps.append(file)
		cfg["ramdisk"] = file

	def load_kernel(self, cfg: dict):
		ctx = self.builder.ctx
		if "image-gzip-dtb" not in cfg or not cfg["image-gzip-dtb"]: return
		kernel = self.resolve_kernel(ctx.get("kernel.kernel"))
		dtb = self.resolve_kernel(ctx.get("kernel.devicetree"))
		if "kernel" in cfg: kernel = self.to_list(cfg["kernel"])
		if "dtb" in cfg: dtb = self.to_list(cfg["dtb"])
		if len(kernel) != 1: raise ArchBuilderConfigError("bad number of kernel")
		if len(dtb) < 1: raise ArchBuilderConfigError("no device tree found")
		fd, file = mkstemp()
		log.debug("creating Image.gz-dtb...")
		with os.fdopen(fd, "wb") as fo:
			with open(kernel[0], "rb") as fi:
				fo.write(gzip.compress(fi.read()))
			for d in dtb:
				with open(d, "rb") as fi:
					fo.write(fi.read())
			size = fo.tell()
		log.debug("size: %u bytes", size)
		cfg.pop("dtb", None)
		cfg["kernel"] = file
		self.temps.append(file)

	def build(self):
		try:
			self.temps = []
			cfg = self.builder.config.copy()
			self.load_initramfs(cfg)
			self.load_kernel(cfg)
			args = self.parse_config(cfg)
			match self.builder.type:
				case "aboot": key = "--output"
				case "avndboot": key = "--vendor_boot"
				case _: raise ArchBuilderConfigError("bad type for abootimg")
			args.extend([key, self.builder.device])
			log.debug("run mkbootimg with %s", " ".join(args))
			mkbootimg(args)
		finally:
			for temp in self.temps:
				os.remove(temp)
