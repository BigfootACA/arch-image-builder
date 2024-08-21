import os
import shutil
from logging import getLogger
from builder.lib import utils
from builder.component import user
from builder.lib.config import ArchBuilderConfigError
from builder.lib.context import ArchBuilderContext
from builder.lib.cgroup import CGroup
log = getLogger(__name__)


def chroot_run(
	ctx: ArchBuilderContext,
	cmd: str | list[str],
	cwd: str = None,
	env: dict = None,
	stdin: str | bytes = None,
	cgroup: CGroup = None,
) -> int:
	"""
	Chroot into rootfs and run programs
	If you are running a cross build, you need install qemu-user-static-binfmt
	"""
	if not ctx.chroot:
		raise RuntimeError("rootfs is not ready for chroot")
	path = ctx.get_rootfs()
	args = ["chroot", path]
	args.extend(utils.parse_cmd_args(cmd))
	return ctx.run_external(args, cwd, env, stdin, cgroup)


def proc_mkdir(ctx: ArchBuilderContext, file: dict, path: str):
	root = ctx.get_rootfs()
	dir_uid, dir_gid, dir_mode = 0, 0, 0o0755
	if "mkdir" in file:
		if type(file["mkdir"]) is bool:
			# mkdir = False: skip mkdir
			if not file["mkdir"]: return
		elif type(file["mkdir"]) is dict:
			if "mode" in file: dir_mode = int(file["mode"])
			dir_uid, dir_gid = user.parse_user_from(ctx, file)
	# mkdir recursive
	def mkdir_loop(folder: str):
		# strip end slash
		if folder.endswith("/"): folder = folder[0:-1]
		if len(folder) == 0: return

		# resolve to rootfs
		real = os.path.join(root, folder)
		if os.path.exists(real): return

		# create parent folder first
		mkdir_loop(os.path.dirname(folder))

		log.debug(f"create folder {real} with {dir_mode:04o}")
		os.mkdir(real, mode=dir_mode)
		log.debug(f"chown folder {real} to {dir_uid}:{dir_gid}")
		os.chown(real, uid=dir_uid, gid=dir_gid)
	mkdir_loop(os.path.dirname(path))


def check_allowed(path: str, action: str):
	"""
	Check add / remove files is in allowed files
	Why we cannot write into others folder?
	1. Write to pacman managed folders (/usr, /opt, ...) WILL BREAK SYSTEM UPGRADE
	2. Never add files to homes (/home/xxx, /root, ...),
		when someone create new users, these configs will broken.
	What if I want to write to other folders?
	1. /usr/bin/ /usr/lib/ /opt/ ...: you should not add files here,
		please make a package and install via pacman.
	2. /home/xxx: add files into /etc/skel, they will copy when user create
	3. /usr/lib/systemd/system: do not add service or override into here,
		please use /etc/systemd/system (see Unit File Load Path in man:systemd.unit(5))
	4. /run /tmp /dev: there are mount as virtual filesystem when booting,
		you can use systemd-tmpfiles to create in these folders (/etc/tmpfiles.d)
	Why these folder is writable
	1. /etc/ is used for administrator configs
	2. /boot/ is used for system boot up, you can put bootloaders configs into this folder
	3. /var/ is used for daemons runtime states
	3. /usr/lib/modules/ is used for kernel modules (custom kernel)
	3. /usr/lib/firmware/ is used for system firmware (custom firmware)
	"""
	allow_list = (
		"/etc/",
		"/boot/",
		"/var/",
		"/usr/lib/modules",
		"/usr/lib/firmware",
	)
	if not path.startswith(allow_list):
		raise ArchBuilderConfigError(f"{action} {path} is not allowed")


def add_file(ctx: ArchBuilderContext, file: dict):
	# at least path content
	if "path" not in file:
		raise ArchBuilderConfigError("no path set in file")
	if "content" not in file and "source" not in file:
		raise ArchBuilderConfigError("no content or source set in file")
	root = ctx.get_rootfs()
	path: str = file["path"]
	if path.startswith("/"): path = path[1:]
	uid, gid = user.parse_user_from(ctx, file)

	# file encoding. default to UTF-8
	encode = file["encode"] if "encode" in file else "utf-8"

	# follow symbolic links
	follow = file["follow"] if "follow" in file else True

	# source is a folder 
	folder = file["folder"] if "folder" in file else False

	# files mode
	mode = int(file["mode"]) if "mode" in file else 0o0644

	check_allowed(file["path"], "add files into")

	# create parent folders
	proc_mkdir(ctx, file, path)

	# resolve to rootfs
	real = os.path.join(root, path)

	if "content" in file:
		if not follow and os.path.exists(real): os.remove(real)
		log.debug(f"create file {real}")
		with open(real, "wb") as f:
			content: str = file["content"]
			log.debug(
				"write to %s with %s",
				real, content.strip()
			)
			f.write(content.encode(encode))
	elif "source" in file:
		src: str = file["source"]
		if not src.startswith("/"):
			src = os.path.join(ctx.dir, src)
		log.debug(f"copy {src} to {real}")
		if folder:
			shutil.copytree(src, real, symlinks=follow, dirs_exist_ok=True)
		else:
			shutil.copyfile(src, real, follow_symlinks=follow)
	else:
		assert False
	log.debug(f"chmod file {real} to {mode:04o}")
	os.chmod(real, mode=mode)
	log.debug(f"chown file {real} to {uid}:{gid}")
	os.chown(real, uid=uid, gid=gid)
	log.info("adding file %s successful", file["path"])


def add_files_all(ctx: ArchBuilderContext, stage: str = None):
	for file in ctx.get("filesystem.files", []):
		cs = file["stage"] if "stage" in file else None
		if cs != stage: continue
		add_file(ctx, file)


def remove_all(ctx: ArchBuilderContext):
	for file in ctx.get("filesystem.remove", []):
		check_allowed(file, "remove files from")
		shutil.rmtree(file)


def proc_filesystem(ctx: ArchBuilderContext):
	add_files_all(ctx)
	remove_all(ctx)
