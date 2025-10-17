import os
from logging import getLogger
from builder.lib.boot import find_efi_folder, get_efi_arch, boot_entry_prepare, boot_install_efi
from builder.lib.context import ArchBuilderContext
from builder.lib.utils import path_to_name
log = getLogger(__name__)


def gen_entry(ctx: ArchBuilderContext, cfg: dict) -> str:
	"""
	Generate a entry config for embloader
	"""
	ret = ""
	entry = boot_entry_prepare(ctx, cfg)

	ret += f"title         {entry["name"]}\n"

	# systemd related
	ret += f"architecture  {get_efi_arch(ctx)}\n"

	# add kernel path field
	ret += f"linux         {entry["kernel"]}\n"

	# add device tree blob field
	if entry["devicetree"]:
		ret += f"devicetree    {entry["devicetree"]}\n"

	# add initramfs field
	if entry["initramfs"]:
		ret += f"initrd        {" ".join(entry["initramfs"])}\n"

	# add device tree blob overlay field
	if entry["dtoverlay"]:
		ret += f"devicetree-overlay  {" ".join(entry["dtoverlay"])}\n"

	# add kernel command line
	ret += f"options       {" ".join(entry["cmdline"])}\n"

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


def proc_systemd_boot(ctx: ArchBuilderContext):
	"""
	Install systemd-boot bootloader entries
	"""
	root = ctx.get_rootfs()
	if "systemd-boot" not in ctx.get("bootloader.method", []):
		return

	esp_dest = find_efi_folder(ctx)

	# esp install target folder in rootfs (WORKSPACE/TARGET/rootfs/boot/efi)
	efi_folder = os.path.join(root, esp_dest)

	# systemd-boot folder
	folder = os.path.join(efi_folder, "loader")
	os.makedirs(folder, exist_ok=True)

	boot_install_efi(
		ctx, "usr/lib/systemd/boot/efi", "efi/systemd",
		f"systemd-boot{get_efi_arch(ctx)}.efi"
	)
	gen_configs(ctx, folder)
