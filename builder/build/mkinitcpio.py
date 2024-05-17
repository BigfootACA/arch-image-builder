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
	modules: list[str] = []
	binaries: list[str] = []
	files: list[str] = []
	hooks: list[str] = []
	hooks.append("base")
	hooks.append("systemd")
	hooks.append("autodetect")
	if ctx.cur_arch in ["x86_64", "i386"]:
		hooks.append("microcode")
	hooks.append("modconf")
	if ctx.get("mkinitcpio.hooks.keymap", False):
		hooks.extend(["kms", "keyboard", "keymap", "consolefont"])
	hooks.extend(["block", "filesystems", "fsck"])
	add_values(ctx, "mkinitcpio.modules", modules)
	add_values(ctx, "mkinitcpio.binaries", binaries)
	add_values(ctx, "mkinitcpio.files", files)
	root = ctx.get_rootfs()
	cfg = os.path.join(root, "etc/mkinitcpio.conf")
	with open_config(cfg) as f:
		f.write("MODULES=(%s)\n" % (" ".join(modules)))
		f.write("BINARIES=(%s)\n" % (" ".join(binaries)))
		f.write("FILES=(%s)\n" % (" ".join(files)))
		f.write("HOOKS=(%s)\n" % (" ".join(hooks)))


def recreate_initrd(ctx: ArchBuilderContext, path: str):
	chroot_run(ctx, ["mkinitcpio", "-p", path])


def recreate_initrd_no_autodetect(ctx: ArchBuilderContext, path: str):
	tmp = os.path.join(ctx.get_rootfs(), "tmp")
	with NamedTemporaryFile("w", dir=tmp) as temp:
		with open(path, "r") as f:
			temp.write(f.read())
		temp.write("\ndefault_options=\"-S autodetect\"\n")
		temp.flush()
		path = os.path.join("/tmp", os.path.basename(temp.name))
		recreate_initrd(ctx, path)


def recreate_initrds(ctx: ArchBuilderContext):
	root = ctx.get_rootfs()
	no_autodetect = ctx.get("mkinitcpio.no_autodetect", True)
	folder = os.path.join(root, "etc/mkinitcpio.d")
	for preset in os.listdir(folder):
		if not preset.endswith(".preset"): continue
		path = os.path.join(folder, preset)
		if not no_autodetect: recreate_initrd(ctx, path)
		else: recreate_initrd_no_autodetect(ctx, path)


def proc_mkinitcpio(ctx: ArchBuilderContext):
	gen_config(ctx)
	recreate_initrds(ctx)
