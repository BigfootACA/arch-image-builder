import os
from logging import getLogger
from builder.lib.context import ArchBuilderContext
from builder.lib.mount import MountTab
log = getLogger(__name__)


def init_rootfs(ctx: ArchBuilderContext):
	"""
	Initialize Arch Linux rootfs
	"""
	path = ctx.get_rootfs()
	def mkdir(mode, *names):
		real = os.path.join(path, *names)
		if not os.path.exists(real):
			log.debug(f"create folder {real} with {mode:04o}")
			os.makedirs(real, mode=mode)
	log.debug(f"initializing rootfs folders at {path}")
	mkdir(0o0755, path)
	mkdir(0o0755, "dev")
	mkdir(0o0555, "proc")
	mkdir(0o0755, "run")
	mkdir(0o0555, "sys")
	mkdir(0o0755, "var", "lib", "pacman")
	mkdir(0o0755, "etc", "pacman.d")
	log.info(f"initialized rootfs folders at {path}")


def undo_mounts(ctx: ArchBuilderContext):
	"""
	Clean up mount points
	"""
	if len(ctx.mounted) <= 0: return
	log.debug("undo mount points")
	ctx.chroot = False
	while len(ctx.mounted) > 0:
		unmounted = 0
		for mount in ctx.mounted.copy():
			try:
				mount.umount()
				ctx.mounted.remove(mount)
				unmounted += 1
			except:
				pass
		if unmounted == 0:
			raise RuntimeError("failed to umount all")
	mnts = MountTab.parse_mounts()
	if any(mnts.find_folder(ctx.work)):
		raise RuntimeError("mount points not cleanup")


def init_mount(ctx: ArchBuilderContext):
	"""
	Setup mount points for rootfs
	"""
	root = ctx.get_rootfs()
	def symlink(target, *names):
		real = os.path.join(root, *names)
		if not os.path.exists(real):
			log.debug(f"create symlink {real} -> {target}")
			os.symlink(target, real)
	def root_mount(source, target, fstype, options):
		real = os.path.realpath(os.path.join(root, target))
		ctx.mount(source, real, fstype, options)
	try:
		# ensure mount point is clean
		mnts = MountTab.parse_mounts()
		if any(mnts.find_folder(ctx.work)):
			raise RuntimeError("mount points not cleanup")

		root_mount("proc", "proc", "proc", "nosuid,noexec,nodev")
		root_mount("sys", "sys", "sysfs", "nosuid,noexec,nodev,ro")
		root_mount("dev", "dev", "devtmpfs", "mode=0755,nosuid")
		root_mount("pts", "dev/pts", "devpts", "mode=0620,gid=5,nosuid,noexec")
		root_mount("shm", "dev/shm", "tmpfs", "mode=1777,nosuid,nodev")
		root_mount("run", "run", "tmpfs", "nosuid,nodev,mode=0755")
		root_mount("tmp", "tmp", "tmpfs", "mode=1777,strictatime,nodev,nosuid")

		# symbolic links for some script tools (e.g. mkinitcpio)
		symlink("/proc/self/fd", "dev", "fd")
		symlink("/proc/self/fd/0", "dev", "stdin")
		symlink("/proc/self/fd/1", "dev", "stdout")
		symlink("/proc/self/fd/2", "dev", "stderr")
		ctx.chroot = True
	except:
		log.error("failed to initialize mount points")
		undo_mounts(ctx)
		raise
