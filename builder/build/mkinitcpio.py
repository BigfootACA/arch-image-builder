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


def parse_preset_file(ctx: ArchBuilderContext, path: str) -> list[dict]:
	"""
	Parse an initramfs preset file
	"""
	snippet = """
	for preset in "${PRESETS[@]}"; do
		eval echo "\\"initrd;${preset};\\$${preset}_image\\"";
	done
	"""
	full_snippet = f"source \"{path}\"\n{snippet}\n"
	ret, data = ctx.run_external(["bash", "-e"], stdin=full_snippet, want_stdout=True)
	if ret != 0:
		raise ArchBuilderConfigError(f"cannot parse initramfs preset {path}")
	ret = []
	for lines in data.splitlines():
		parts = lines.split(";")
		if len(parts) != 3 or parts[0] != "initrd":
			continue
		real_image = os.path.join(ctx.get_rootfs(), parts[2].lstrip("/"))
		ret.append({
			"preset": parts[1],
			"path": parts[2],
			"real_path": real_image,
		})
	return ret


def recreate_initrd(ctx: ArchBuilderContext, path: str):
	"""
	Create a full initramfs without autodetect
	In build stage, mkinitcpio can not find out needs modules, it will cause unbootable.
	"""
	fake_autodetect_snippet = """
	build() {
		declare -gri mkinitcpio_autodetect=1
		_autodetect_cache[_placeholder_]=1
		return 0
	}
	help() {
		echo "Fake autodetect hook for arch-image-builder"
	}
	"""
	tmp = os.path.join(ctx.get_rootfs(), "tmp")
	presets = parse_preset_file(ctx, path)
	for preset in presets:
		if os.path.exists(preset["real_path"]):
			log.debug(f"remove old initramfs {preset["real_path"]}")
			os.remove(preset["real_path"])

	autodetect_path = None

	with NamedTemporaryFile("w", dir=tmp) as temp:

		# copy original preset
		with open(path, "r") as f:
			temp.write(f.read())

		# skip autodetect or use fake one
		if ctx.get("mkinitcpio.fake_autodetect", True):
			autodetect_path = os.path.join(ctx.get_rootfs(), "usr/lib/initcpio/install/autodetect")
			if os.path.exists(autodetect_path + ".bak"):
				os.remove(autodetect_path)
			else:
				os.rename(autodetect_path, autodetect_path + ".bak")
			with open(autodetect_path, "w") as f:
				f.write(fake_autodetect_snippet)
			log.debug("use fake autodetect hook")
		elif ctx.get("mkinitcpio.no_autodetect", False):
			temp.write("\ndefault_options=\"-S autodetect\"\n")

		# skip fallback
		if ctx.get("mkinitcpio.no_fallback", True):
			if len(presets) > 0:
				presets = [p for p in presets if p["preset"] != "fallback"]
				val_presets = [p["preset"] for p in presets]
				temp.write(f'PRESETS=({" ".join(val_presets)})\n')
			else:
				log.warning(f"cannot find any preset in {path}")

		temp.flush()

		# run mkinitcpio (with path in rootfs)
		preset_path = os.path.join("/tmp", os.path.basename(temp.name))
		ret = chroot_run(ctx, ["mkinitcpio", "-p", preset_path])
		if ret != 0 and not any(os.path.exists(file["real_path"]) for file in presets):
			raise ArchBuilderConfigError(f"failed to create initramfs: {ret}")

	if autodetect_path and os.path.exists(autodetect_path) and os.path.exists(autodetect_path + ".bak"):
		os.remove(autodetect_path)
		os.rename(autodetect_path + ".bak", autodetect_path)


def recreate_initrds(ctx: ArchBuilderContext):
	"""
	Regenerate all initramfs
	"""
	root = ctx.get_rootfs()
	folder = os.path.join(root, "etc/mkinitcpio.d")
	if not os.path.exists(folder):
		log.debug("skip recreate initrds")
		return

	# scan all initramfs preset and regenerate them
	for preset in os.listdir(folder):
		if not preset.endswith(".preset"): continue
		recreate_initrd(ctx, os.path.join(folder, preset))


def proc_mkinitcpio(ctx: ArchBuilderContext):
	"""
	Process mkinitcpio options
	"""
	gen_config(ctx)
	recreate_initrds(ctx)
