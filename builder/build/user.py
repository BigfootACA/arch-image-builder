from logging import getLogger
from builder.build.filesystem import chroot_run
from builder.lib.config import ArchBuilderConfigError
from builder.lib.context import ArchBuilderContext
log = getLogger(__name__)


def proc_user(ctx: ArchBuilderContext, cfg: dict):
	"""
	Create a new user and set password
	"""
	if "name" not in cfg: raise ArchBuilderConfigError("username not set")
	name = cfg["name"]
	cmds = []
	if ctx.passwd.lookup_name(name) is None:
		# user is not exists, create it
		cmds.append("useradd")
		cmds.append("-m") # create home
		action = "created"
	else:
		# user is already exists, modify it
		cmds.append("usermod")
		action = "modified"

	# add all options
	if "uid" in cfg: cmds.extend(["-u", str(cfg["uid"])])
	if "gid" in cfg: cmds.extend(["-g", str(cfg["gid"])])
	if "home" in cfg: cmds.extend(["-d", cfg["home"]])
	if "shell" in cfg: cmds.extend(["-s", cfg["shell"]])
	if "groups" in cfg: cmds.extend(["-G", str(cfg["groups"])])
	cmds.append(name)

	# run useradd or usermod
	ret = chroot_run(ctx, cmds)
	if ret != 0: raise OSError(f"{cmds[0]} failed")

	# we want to set a password for user
	if "password" in cfg:
		cmds = ["chpasswd"]
		text = f"{name}:{cfg['password']}\n"
		ret = chroot_run(ctx, cmds, stdin=text)
		if ret != 0: raise OSError("chpasswd failed")

	# reload user database
	ctx.reload_passwd()
	log.info(f"{action} user {name}")


def proc_group(ctx: ArchBuilderContext, cfg: dict):
	"""
	Create a new group
	"""
	if "name" not in cfg: raise ArchBuilderConfigError("groupname not set")
	name = cfg["name"]
	cmds = []
	if ctx.passwd.lookup_name(name) is None:
		# group is not exists, create it
		cmds.append("groupadd")
		action = "created"
	else:
		# group is already exists, modify it
		cmds.append("groupmod")
		action = "modified"

	# add all options
	if "gid" in cfg: cmds.extend(["-g", str(cfg["gid"])])
	cmds.append(name)

	# run groupadd or groupmod
	ret = chroot_run(ctx, cmds)
	if ret != 0: raise OSError(f"{name} failed")

	# reload user database
	ctx.reload_passwd()
	log.info(f"{action} group {name}")


def proc_users(ctx: ArchBuilderContext):
	"""
	Create all users
	"""
	for user in ctx.get("sysconf.user", []):
		proc_user(ctx, user)


def proc_groups(ctx: ArchBuilderContext):
	"""
	Create all groups
	"""
	for group in ctx.get("sysconf.group", []):
		proc_group(ctx, group)


def proc_usergroup(ctx: ArchBuilderContext):
	"""
	Create all users and groups
	"""
	proc_groups(ctx) # create groups before users
	proc_users(ctx)
