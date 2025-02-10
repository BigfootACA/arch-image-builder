import os
import shutil
from logging import getLogger
from builder.lib.context import ArchBuilderContext
from builder.lib.config import ArchBuilderConfigError
from builder.lib.loop import loop_get_backing, loop_get_offset
from builder.lib.blkid import Blkid
from builder.lib.mount import MountPoint
log = getLogger(__name__)


blkid = Blkid()
modules = [
	"part_msdos", "part_gpt", "part_apple", "ext2", "fat", "ntfs", "sleep",
	"ufs1", "ufs2", "cpio", "sleep", "search", "search_fs_file", "minicmd", 
	"search_fs_uuid", "search_label", "reboot", "halt", "gzio", "serial",
	"boot", "file", "f2fs", "iso9660", "hfs", "hfsplus", "zfs", "minix",
	"memdisk", "sfs", "lvm", "http", "tftp", "udf", "xfs", "date", "echo",
	"all_video", "btrfs", "disk", "configfile", "terminal",
]


def get_prop(
	ctx: ArchBuilderContext,
	name: str,
	cfg: dict,
	path: bool = False,
	multi: bool = False,
) -> str | None:
	"""
	Get a config value for grub
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


def fstype_to_mod(name: str) -> str:
	"""
	Map filesystem type to GRUB2 modules name
	"""
	match name:
		case "ext3": return "ext2"
		case "ext4": return "ext2"
		case "vfat": return "fat"
		case "fat12": return "fat"
		case "fat16": return "fat"
		case "fat32": return "fat"
		case "msdos": return "fat"
		# TODO: add more filesystems
		case _: return name


def gen_menuentry(ctx: ArchBuilderContext, cfg: dict) -> str:
	"""
	Generate a menuentry config for grub
	"""
	ret = ""

	# menuentry name (default to Linux)
	name = cfg["name"] if "name" in cfg else "Linux"

	# kernel image path
	kernel = get_prop(ctx, "kernel", cfg, True)

	# initramfs image path (supports multiples)
	initramfs = get_prop(ctx, "initramfs", cfg, True, True)

	# device tree blob path (supports multiples)
	devicetree = get_prop(ctx, "devicetree", cfg, True, True)

	# kernel command line
	cmdline = get_prop(ctx, "cmdline", cfg, False, True)

	# the folder to place these files
	path = get_prop(ctx, "path", cfg, False, False)

	if kernel is None: raise ArchBuilderConfigError("no kernel for grub")
	if cmdline is None: cmdline = ""
	ret += f"menuentry '{name}' {{\n"

	# if path set: load filesystem module and search to set root
	if path:
		# find out the mount point in fstab
		fs = ctx.fstab.find_target(path)
		if fs is None or len(fs) == 0 or fs[0] is None:
			raise ArchBuilderConfigError(f"mountpoint {path} not found")
		dev = fs[0].source

		# map to virtual file system
		if dev in ctx.fsmap: dev = ctx.fsmap[dev]

		# get the filesystem UUID to search
		uuid = blkid.get_tag_value(None, "UUID", dev)
		if uuid is None: raise RuntimeError(f"cannot detect uuid for {path}")

		# load filesystem module and search target
		ret += "\tinsmod %s\n" % fstype_to_mod(fs[0].fstype)
		ret += f"\tsearch --no-floppy --fs-uuid --set=root {uuid}\n"

	# add device tree blob field
	if devicetree:
		ret += "\techo 'Loading Device Tree...'\n"
		ret += f"\tdevicetree {devicetree}\n"

	# add kernel path field and kernel command line
	ret += "\techo 'Loading Kernel...'\n"
	ret += f"\tlinux {kernel} {cmdline}\n"

	# add initramfs field
	if initramfs:
		ret += "\techo 'Loading Initramfs...'\n"
		ret += f"\tinitrd {initramfs}\n"

	# boot into linux (not add 'boot' command, its imply by menuentry)
	ret += "\techo 'Booting...'\n"
	ret += f"}}\n"
	return ret


def gen_basic(ctx: ArchBuilderContext) -> str:
	ret = ""

	# load generic modules
	ret += "insmod part_gpt\n"
	ret += "insmod part_msdos\n"
	ret += "insmod all_video\n"

	# setup console and serial
	ret += "terminal_input console\n"
	ret += "terminal_output console\n"
	ret += "if serial --unit=0 --speed=115200; then\n"
	ret += "\tterminal_input --append console\n"
	ret += "\tterminal_output --append console\n"
	ret += "fi\n"

	# set grub timeout seconds
	ret += "set timeout_style=menu\n"
	timeout = ctx.get("bootloader.timeout", 5)
	ret += f"set timeout={timeout}\n"

	# find out the default entry
	default = 0
	items = ctx.get("bootloader.items", [])
	for idx in range(len(items)):
		item = items[idx]
		if "default" in item and item["default"]:
			default = idx
	ret += f"set default={default}\n"

	return ret


def mkconfig(ctx: ArchBuilderContext) -> str:
	"""
	Generate a full grub config for current rootfs
	"""
	ret = ""
	ret += gen_basic(ctx)
	for item in ctx.get("bootloader.items", []):
		ret += gen_menuentry(ctx, item)
	return ret


def proc_targets(ctx: ArchBuilderContext, install: str):
	"""
	Copy grub target folder directly
	"""
	copies = [".mod", ".lst"]
	folder = os.path.join(ctx.get_rootfs(), "usr/lib/grub")
	for target in ctx.get("grub.targets", []):
		# target name format: i386-pc, arm64-efi
		if "/" in target: raise ArchBuilderConfigError(f"bad target {target}")
		base = os.path.join(folder, target)

		# at least we need linux.mod
		if not os.path.exists(os.path.join(base, "linux.mod")):
			raise ArchBuilderConfigError(f"target {target} not found")
		dest = os.path.join(install, target)
		os.makedirs(dest, mode=0o0755, exist_ok=True)

		# copy grub target
		for file in os.listdir(base):
			if not any((file.endswith(name) for name in copies)):
				continue
			shutil.copyfile(
				os.path.join(base, file),
				os.path.join(dest, file),
			)
		log.info(f"installed grub target {target}")


def proc_config(ctx: ArchBuilderContext, install: str):
	"""
	Generate a full grub config for current rootfs and write to install folder
	"""
	if "items" not in ctx.get("bootloader"):
		return
	content = mkconfig(ctx)
	cfg = os.path.join(install, "grub.cfg")
	with open(cfg, "w") as f:
		f.write(content)
	log.info(f"generated grub config {cfg}")


def efi_arch_name(target: str) -> str:
	"""
	Map grub target name to UEFI arch name
	"""
	match target:
		case "arm64-efi": return "aa64"
		case "x86_64-efi": return "x64"
		case "arm-efi": return "arm"
		case "i386-efi": return "ia32"
		case "riscv64-efi": return "riscv64"
		case _: raise RuntimeError(
			f"unsupported {target} for efi name"
		)


def efi_boot_name(target: str) -> str:
	"""
	Map grub target name to UEFI default boot file name
	"""
	name = efi_arch_name(target)
	return f"boot{name}.efi"


def proc_mkimage_efi(ctx: ArchBuilderContext, target: str):
	"""
	Create GRUB EFI image for boot
	"""
	cmds = ["grub-mkimage"]
	root = ctx.get_rootfs()

	# allowed esp folders
	efi_folders = ["/boot", "/boot/efi", "/efi", "/esp"]

	# grub2 source folder in rootfs (WORKSPACE/TARGET/rootfs/usr/lib/grub/x86_64-efi)
	base = os.path.join(root, "usr/lib/grub", target)

	# install path in rootfs (/boot/grub)
	install = ctx.get("grub.path", "/boot/grub")

	# why this function called proc_mkimage_efi?
	if not target.endswith("-efi"):
		raise RuntimeError("mkimage efi only for *-efi")

	# must ends with /
	fdir = os.path.realpath(install) + "/"

	# find out requires mount point
	esp: MountPoint | None = None # UEFI system partition
	grub: MountPoint | None = None # GRUB install folder
	for mnt in ctx.fstab:
		# esp must be fat
		if fstype_to_mod(mnt.fstype) == "fat":
			if mnt.target in efi_folders:
				esp = mnt

		# add an end slash to avoid same prefix (likes /boot /bootfs)
		tdir = mnt.target
		if not tdir.endswith("/"): tdir += "/"

		# grub install folder
		if fdir.startswith(tdir):
			# find out the deepest mount point
			# to avoid / but installed in /boot
			if (not grub) or mnt.level >= grub.level:
				grub = mnt
	if grub is None: raise RuntimeError("grub install folder not found")

	# grub install target folder (/boot/grub)
	if not install.startswith("/"):
		install = "/" + install

	# must in grub install folder
	if not install.startswith(grub.target):
		raise RuntimeError("grub install prefix not found")

	# get grub install path in target partition
	#  Mount  GRUB Install  Prefix
	#  /boot  /boot/grub    /grub
	#  /      /boot/grub    /boot/grub
	prefix = install[len(grub.target):]
	if not prefix.startswith("/"): prefix = "/" + prefix

	# get UUID of grub installed filesystem UUID
	device = (ctx.fsmap[grub.source] if grub.source in ctx.fsmap else grub.source)
	uuid = blkid.get_tag_value(None, "UUID", device)
	if not uuid: raise RuntimeError(
		"failed to detect uuid for grub install path"
	)

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

	# grub install target folder in rootfs (WORKSPACE/TARGET/rootfs/boot/grub)
	grub_folder = os.path.join(root, install[1:])

	cmds.append(f"--format={target}")
	cmds.append(f"--directory={base}")
	cmds.append(f"--prefix={prefix}")
	cmds.append("--compression=xz")

	# put builtin config into grub install folder
	builtin = os.path.join(grub_folder, "grub.builtin.cfg")
	with open(builtin, "w") as f:
		f.write(f"search --no-floppy --fs-uuid --set=root {uuid}\n")
		f.write(f"set prefix=\"($root){prefix}\"\n")
		f.write("normal\n")
		f.write("echo \"Failed to switch into normal mode\"\n")
		f.write("sleep 5\n")
	cmds.append(f"--config={builtin}")

	# efi boot image install folder (WORKSPACE/TARGET/rootfs/boot/efi/efi/boot)
	efi = os.path.join(efi_folder, "efi/boot")
	os.makedirs(efi, mode=0o0755, exist_ok=True)

	# efi boot image (WORKSPACE/TARGET/rootfs/boot/efi/efi/boot/bootx64.efi)
	out = os.path.join(efi, efi_boot_name(target))
	cmds.append(f"--output={out}")
	if os.path.exists(out): os.remove(out)

	cmds.extend(modules)

	# run grub-mkimage
	ret = ctx.run_external(cmds)
	if ret != 0: raise OSError("grub-mkimage failed")
	log.info(f"generated grub {target} efi image {out}")


def proc_bootsec(ctx: ArchBuilderContext, target: str):
	"""
	Install boot sector for x86 PC for grub-install
	"""
	mods = []
	cmds = ["grub-install"]
	if target != "i386-pc":
		raise RuntimeError("bootsec only for i386-pc")
	mount = ctx.get_mount()
	root = ctx.get_rootfs()

	# get grub install base folder (boot)
	install: str = ctx.get("grub.path", "/boot/grub")
	if install.startswith("/"): install = install[1:]
	if install.endswith("/grub"): install = install[:-5]

	grub = os.path.join(root, "usr/lib/grub", target)

	cmds.append(f"--target={target}")
	cmds.append(f"--directory={grub}")

	mods.append("part_msdos")
	mods.append("part_gpt")

	# grub install base folder in mount (WORKSPACE/TARGET/mount/boot)
	mnt_install = os.path.join(mount, install)
	cmds.append(f"--boot-directory={mnt_install}")

	# find out mount point of rootfs
	rootfs = ctx.fstab.find_target("/")
	if rootfs is None or len(rootfs) <= 0 or rootfs[0] is None:
		raise RuntimeError("rootfs mount point not found")
	rootfs = rootfs[0]

	# add filesystem module for rootfs
	mods.append(fstype_to_mod(rootfs.fstype))
	if len(mods) > 0:
		cmds.append("--modules=" + (" ".join(mods)))

	# detect grub boot sector install device
	device = ctx.get("grub.device", None)
	if device is None:
		source = rootfs.source
		if source in ctx.fsmap:
			source = ctx.fsmap[source]

		# loop setup by builder.disk.image.ImageBuilder
		if not source.startswith("/dev/loop"):
			raise RuntimeError("no device to detect grub install")

		# loop offset partition setup by builder.disk.layout.build.DiskLayoutBuilder
		if loop_get_offset(source) <= 0:
			raise RuntimeError("no loop part to detect grub install")

		# backing as parent disk
		device = loop_get_backing(source)
	if device is None:
		raise RuntimeError("no device for grub install")
	cmds.append(device)

	# run grub-install
	ret = ctx.run_external(cmds)
	if ret != 0: raise OSError("grub-install failed")

	# copy grub installed target from mount to rootfs
	src = os.path.join(mnt_install, "grub")
	dst = os.path.join(root, install, "grub")
	shutil.copytree(src, dst, dirs_exist_ok=True)


def proc_install(ctx: ArchBuilderContext):
	"""
	Process GRUB targets install
	"""
	targets: list[str] = ctx.get("grub.targets", [])
	for target in targets:
		if target == "i386-pc":
			proc_bootsec(ctx, target)
		elif target.endswith("-efi"):
			proc_mkimage_efi(ctx, target)
		else: raise ArchBuilderConfigError(
			f"unsupported target {target}"
		)


def proc_grub(ctx: ArchBuilderContext):
	"""
	Install GRUB bootloader
	"""
	root = ctx.get_rootfs()
	if "grub" not in ctx.config:
		return

	# get grub install folder in rootfs (WORKSPACE/TARGET/rootfs/boot/grub)
	install: str = ctx.get("grub.path", "/boot/grub")
	if install.startswith("/"):
		install = install[1:]
	install = os.path.join(root, install)
	os.makedirs(install, mode=0o0755, exist_ok=True)

	proc_config(ctx, install)
	proc_targets(ctx, install)
	proc_install(ctx)
