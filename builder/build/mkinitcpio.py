import os
from logging import getLogger
from tempfile import NamedTemporaryFile
from builder.build.filesystem import chroot_run
from builder.lib.context import ArchBuilderContext
from builder.lib.config import ArchBuilderConfigError
from builder.lib.utils import open_config
log = getLogger(__name__)


def add_values(ctx: ArchBuilderContext, key: str, arr: list[str]):
	vals = ctx.get(key, [])
	vt = type(vals)
	if vt is list: arr.extend(vals)
	elif vt is str: arr.extend(vals.split())
	else: raise ArchBuilderConfigError(f"bad values for {key}")


def gen_config(ctx: ArchBuilderContext):
	"""
	Generate mkinitcpio.conf
	"""
	modules: list[str] = []
	binaries: list[str] = []
	files: list[str] = []
	hooks: list[str] = []

	# add default hooks
	hooks.append("base")
	hooks.append("systemd")
	hooks.append("autodetect")

	# add microcode if x86_64 (amd-ucode, intel-ucode)
	if ctx.cur_arch in ["x86_64", "i386"]:
		hooks.append("microcode")

	hooks.append("modconf")

	# do not add keymap by default
	if ctx.get("mkinitcpio.hooks.keymap", False):
		hooks.extend(["kms", "keymap", "consolefont"])

	hooks.extend(["keyboard", "block", "filesystems", "fsck"])

	# add others values
	add_values(ctx, "mkinitcpio.modules", modules)
	add_values(ctx, "mkinitcpio.binaries", binaries)
	add_values(ctx, "mkinitcpio.files", files)

	compress = ctx.get("mkinitcpio.compress", None)

	# write mkinitcpio.conf to rootfs
	root = ctx.get_rootfs()
	cfg = os.path.join(root, "etc/mkinitcpio.conf")
	with open_config(cfg) as f:
		f.write("MODULES=(%s)\n" % (" ".join(modules)))
		f.write("BINARIES=(%s)\n" % (" ".join(binaries)))
		f.write("FILES=(%s)\n" % (" ".join(files)))
		f.write("HOOKS=(%s)\n" % (" ".join(hooks)))
		if compress is not None:
			f.write(f"COMPRESSION=\"{compress}\"\n")
		# TODO: add more options


def recreate_initrd(ctx: ArchBuilderContext, path: str):
	"""
	Really run mkinitcpio
	"""
	chroot_run(ctx, ["mkinitcpio", "-p", path])
	# do not check return value of mkinitcpio


def recreate_initrd_no_autodetect(ctx: ArchBuilderContext, path: str):
	"""
	Create a full initramfs without autodetect
	In build stage, mkinitcpio can not find out needs modules, it will cause unbootable.
	"""
	tmp = os.path.join(ctx.get_rootfs(), "tmp")
	with NamedTemporaryFile("w", dir=tmp) as temp:

		# copy original preset
		with open(path, "r") as f:
			temp.write(f.read())

		# skip autodetect
		temp.write("\ndefault_options=\"-S autodetect\"\n")
		temp.flush()

		# run mkinitcpio (with path in rootfs)
		path = os.path.join("/tmp", os.path.basename(temp.name))
		recreate_initrd(ctx, path)


def recreate_initrds(ctx: ArchBuilderContext):
	"""
	Regenerate all initramfs
	"""
	root = ctx.get_rootfs()
	no_autodetect = ctx.get("mkinitcpio.no_autodetect", True)
	folder = os.path.join(root, "etc/mkinitcpio.d")
	if not os.path.exists(folder):
		log.debug("skip recreate initrds")
		return

	# scan all initramfs preset and regenerate them
	for preset in os.listdir(folder):
		if not preset.endswith(".preset"): continue
		path = os.path.join(folder, preset)
		if not no_autodetect: recreate_initrd(ctx, path)
		else: recreate_initrd_no_autodetect(ctx, path)


def proc_mkinitcpio(ctx: ArchBuilderContext):
	"""
	Process mkinitcpio options
	"""
	gen_config(ctx)
	recreate_initrds(ctx)
