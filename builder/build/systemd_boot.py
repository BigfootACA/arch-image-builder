import os
import shutil
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
	Get a config value for systemd-boot
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


def get_efi_arch(ctx: ArchBuilderContext) -> str:
	match ctx.tgt_arch:
		case "aarch64": return "aa64"
		case "x86_64": return "x64"
		case "armv7h": return "arm"
		case _: raise ValueError(f"unsupported architecture {ctx.tgt_arch}")


def gen_entry(ctx: ArchBuilderContext, cfg: dict) -> str:
	"""
	Generate a entry config for systemd-boot
	"""
	ret = ""

	# entry name (default to Linux)
	name = cfg.get("name", "Linux")

	# kernel image path
	kernel = get_prop(ctx, "kernel", cfg, True)

	# initramfs image path (supports multiples)
	initramfs = get_prop(ctx, "initramfs", cfg, True, True)

	# device tree blob path (supports multiples)
	devicetree = get_prop(ctx, "devicetree", cfg, True, True)

	# kernel command line
	cmdline = get_prop(ctx, "cmdline", cfg, False, True)

	if kernel is None: raise ArchBuilderConfigError("no kernel for systemd-boot")
	if cmdline is None: cmdline = ""
	ret += f"title         {name}\n"

	# systemd related
	ret += f"architecture  {get_efi_arch(ctx)}\n"

	# add kernel path field
	ret += f"linux         {kernel}\n"

	# add device tree blob field
	if devicetree:
		ret += f"devicetree    {devicetree}\n"

	# add initramfs field
	if initramfs:
		ret += f"initrd        {initramfs}\n"

	# add kernel command line
	ret += f"options       {cmdline}\n"

	return ret


def gen_configs(ctx: ArchBuilderContext, folder: str):
	entries = os.path.join(folder, "entries")
	os.makedirs(entries, exist_ok=True)
	idx = 0
	default: str = None
	for item in ctx.get("bootloader.items", []):
		name = item.get("name", "Linux")
		id = item.get("id", path_to_name(name))
		key = f"{idx:03d}-{id}"
		if item.get("default", False):
			default = key
		idx += 1
		path = os.path.join(entries, f"{key}.conf")
		entry = gen_entry(ctx, item)
		log.debug(f"create systemd-boot entry config {path}\n{entry}")
		with open(path, "w") as f:
			f.write(entry)

	# create loader.conf
	loader_conf = os.path.join(folder, "loader.conf")
	content = ""
	content += "console-mode keep\n"
	content += "editor on\n"
	timeout = ctx.get("bootloader.timeout", 5)
	if timeout >= 0:
		content += f"timeout {timeout}\n"
	if default is not None:
		content += f"default {default}\n"
	log.debug(f"create systemd-boot loader config {loader_conf}\n{content}")
	with open(loader_conf, "w") as f:
		f.write(content)


def install_efi(ctx: ArchBuilderContext, efi_folder: str):
	efi_arch = get_efi_arch(ctx)
	root = ctx.get_rootfs()
	loader = f"systemd-boot{efi_arch}.efi"
	efi_loader = f"boot{efi_arch}.efi"

	path = os.path.join(root, "usr/lib/systemd/boot/efi", loader)
	if not os.path.exists(path):
		raise FileNotFoundError(f"systemd-boot loader {path} not found")
	log.info(f"use systemd-boot loader {loader}")

	boot_dir = os.path.join(efi_folder, "efi/boot")
	systemd_dir = os.path.join(efi_folder, "efi/systemd")
	os.makedirs(boot_dir, exist_ok=True)
	os.makedirs(systemd_dir, exist_ok=True)

	boot_file = os.path.join(boot_dir, efi_loader)
	systemd_file = os.path.join(systemd_dir, loader)

	log.info(f"install {path} to {systemd_file}")
	shutil.copyfile(path, systemd_file)

	if not os.path.exists(boot_file):
		log.info(f"install {path} to {boot_file}")
		shutil.copyfile(path, boot_file)


def proc_systemd_boot(ctx: ArchBuilderContext):
	"""
	Install systemd-boot bootloader entries
	"""
	# allowed esp folders
	efi_folders = ["/boot", "/boot/efi", "/efi", "/esp"]

	root = ctx.get_rootfs()
	if "systemd-boot" not in ctx.get("bootloader.method", []):
		return

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

	# esp install target folder in rootfs (WORKSPACE/TARGET/rootfs/boot/efi)
	efi_folder = os.path.join(root, esp_dest)

	# systemd-boot folder
	folder = os.path.join(efi_folder, "loader")
	os.makedirs(folder, exist_ok=True)

	install_efi(ctx, efi_folder)
	gen_configs(ctx, folder)
