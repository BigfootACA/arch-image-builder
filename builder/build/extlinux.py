import os
from logging import getLogger
from builder.lib.context import ArchBuilderContext
from builder.lib.config import ArchBuilderConfigError
from builder.lib.mount import MountPoint
from builder.lib.utils import path_to_name
log = getLogger(__name__)


def get_prop(
	ctx: ArchBuilderContext,
	name: str,
	cfg: dict,
	path: bool = False,
	multi: bool = False,
) -> str | None:
	"""
	Get a config value for extlinux
	"""
	value = ctx.get(f"kernel.{name}", None)
	if name in cfg: value = cfg[name]
	if value is None: return None
	if type(value) is str:
		value = [value]
	if len(value) == 0: return None
	if path:
		# must starts with /
		for i in range(len(value)):
			if not value[i].startswith("/"):
				value[i] = "/" + value[i]
	if multi: value = " ".join(value)
	else: value = value[0]
	return value


def gen_entry(ctx: ArchBuilderContext, cfg: dict) -> str:
	"""
	Generate a entry config for extlinux
	"""
	ret = ""

	# entry name (default to Linux)
	name = cfg.get("name", "Linux")

	# entry id
	id = cfg.get("id", path_to_name(name))

	# kernel image path
	kernel = get_prop(ctx, "kernel", cfg, True)

	# initramfs image path (supports multiples)
	initramfs = get_prop(ctx, "initramfs", cfg, True, True)

	# device tree blob path (supports multiples)
	devicetree = get_prop(ctx, "devicetree", cfg, True, True)

	# kernel command line
	cmdline = get_prop(ctx, "cmdline", cfg, False, True)

	if kernel is None: raise ArchBuilderConfigError("no kernel for extlinux")
	if cmdline is None: cmdline = ""

	ret += f"label {id}\n"

	ret += f"\tmenu label {name}\n"

	# add kernel path field
	ret += f"\tkernel {kernel}\n"

	# add device tree blob field
	if devicetree:
		ret += f"\tfdt {devicetree}\n"

	# add initramfs field
	if initramfs:
		ret += f"\tinitrd {initramfs}\n"

	# add kernel command line
	ret += f"\tappend {cmdline}\n"

	return ret


def gen_configs(ctx: ArchBuilderContext, folder: str):
	entries = ""
	default: str = None
	for item in ctx.get("bootloader.items", []):
		name = item.get("name", "Linux")
		id = item.get("id", path_to_name(name))
		if item.get("default", False):
			default = id
		entries += "\n"
		entries += gen_entry(ctx, item)

	# create extlinux.conf
	extlinux_conf = os.path.join(folder, "extlinux.conf")
	content = ""
	timeout = ctx.get("bootloader.timeout", 5)
	if timeout >= 0:
		content += f"timeout {timeout}\n"
	if default is not None:
		content += f"default {default}\n"
	content += entries
	log.debug(f"create extlinux config {extlinux_conf}\n{content}")
	with open(extlinux_conf, "w") as f:
		f.write(content)

def proc_extlinux(ctx: ArchBuilderContext):
	"""
	Install extlinux bootloader entries (U-Boot)
	"""
	# allowed esp folders
	efi_folders = ["/boot", "/boot/efi", "/efi", "/esp"]

	root = ctx.get_rootfs()
	if "extlinux" not in ctx.get("bootloader.method", []):
		return

	# find out requires mount point
	esp: MountPoint | None = None # UEFI system partition
	for mnt in ctx.fstab:
		# esp must be fat
		if mnt.fstype in ["vfat", "fat", "fat32", "fat16", "fat12", "msdos"]:
			if mnt.target in efi_folders:
				esp = mnt
	if esp is None: raise RuntimeError("efi partition not found")

	# esp install target folder (boot/efi)
	esp_dest = esp.target
	if esp_dest.startswith("/"):
		esp_dest = esp_dest[1:]

	# esp install target folder in rootfs (WORKSPACE/TARGET/rootfs/boot/efi)
	efi_folder = os.path.join(root, esp_dest)

	# extlinux folder
	folder = os.path.join(efi_folder, "extlinux")
	os.makedirs(folder, exist_ok=True)

	gen_configs(ctx, folder)
