import os
import shutil
from logging import getLogger
from builder.lib.context import ArchBuilderContext
from builder.lib.config import ArchBuilderConfigError
from builder.lib.mount import MountPoint
log = getLogger(__name__)


def get_efi_arch(ctx: ArchBuilderContext) -> str:
	match ctx.tgt_arch:
		case "aarch64": return "aa64"
		case "x86_64": return "x64"
		case "armv7h": return "arm"
		case _: raise ValueError(f"unsupported architecture {ctx.tgt_arch}")


def find_efi_folder(ctx: ArchBuilderContext) -> str:
	"""
	Find out the EFI system partition mount point
	"""
	# allowed esp folders
	efi_folders = ["/boot", "/boot/efi", "/efi", "/esp"]

	# find out requires mount point
	esp: MountPoint | None = None # UEFI system partition
	for mnt in ctx.fstab:
		# esp must be fat
		if mnt.fstype in ["vfat", "fat", "fat32", "fat16", "fat12", "msdos"]:
			if mnt.target in efi_folders:
				esp = mnt

	# esp install target folder (boot/efi)
	if esp is None:
		log.warning("efi partition not found, use /boot/efi")
		esp_dest = "boot/efi"
	else:
		esp_dest = esp.target
	if esp_dest.startswith("/"):
		esp_dest = esp_dest[1:]

	return esp_dest


def boot_get_prop(
	ctx: ArchBuilderContext,
	name: str,
	cfg: dict,
	path: bool = False,
	multi: bool = False,
) -> str | list[str] | None:
	"""
	Get a config value for boot
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
	if not multi: value = value[0]
	return value


def boot_entry_prepare(ctx: ArchBuilderContext, cfg: dict) -> dict:
	"""
	Prepare bootloader entry info
	"""
	
	# entry name (default to Linux)
	name = cfg.get("name", "Linux")

	# kernel image path
	kernel = boot_get_prop(ctx, "kernel", cfg, path=True, multi=False)

	# initramfs image path (supports multiples)
	initramfs = boot_get_prop(ctx, "initramfs", cfg, path=True, multi=True)

	# device tree blob path
	devicetree = boot_get_prop(ctx, "devicetree", cfg, path=True, multi=False)

	# device tree blob overlay path (supports multiples)
	dtoverlay = boot_get_prop(ctx, "dtoverlay", cfg, path=True, multi=True)

	# kernel command line
	cmdline = boot_get_prop(ctx, "cmdline", cfg, path=False, multi=True)

	if kernel is None: raise ArchBuilderConfigError("no kernel for boot entry")
	if cmdline is None: cmdline = ""

	return {
		"name": name,
		"kernel": kernel,
		"initramfs": initramfs,
		"devicetree": devicetree,
		"dtoverlay": dtoverlay,
		"cmdline": cmdline,
	}


def boot_install_efi(ctx: ArchBuilderContext, src_path: str, ins_path: str, filename: str):
	root = ctx.get_rootfs()
	efi_folder = os.path.join(root, find_efi_folder(ctx))
	src_file = os.path.join(root, src_path, filename)

	if not os.path.exists(src_file):
		raise FileNotFoundError(f"efi loader {src_file} not found")

	boot_dir = os.path.join(efi_folder, "efi/boot")
	ins_dir = os.path.join(efi_folder, ins_path)
	os.makedirs(boot_dir, exist_ok=True)
	os.makedirs(ins_dir, exist_ok=True)

	boot_file = os.path.join(boot_dir, f"boot{get_efi_arch(ctx)}.efi")
	ins_file = os.path.join(ins_dir, filename)

	log.info(f"install {src_file} to {ins_file}")
	shutil.copyfile(src_file, ins_file)

	if not os.path.exists(boot_file):
		log.info(f"install {src_file} to {boot_file}")
		shutil.copyfile(src_file, boot_file)
