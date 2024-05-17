from logging import getLogger
from builder.build.filesystem import chroot_run
from builder.lib.config import ArchBuilderConfigError
from builder.lib.context import ArchBuilderContext
log = getLogger(__name__)


def proc_user(ctx: ArchBuilderContext, cfg: dict):
	if "name" not in cfg: raise ArchBuilderConfigError("username not set")
	name = cfg["name"]
	cmds = []
	if ctx.passwd.lookup_name(name) is None:
		cmds.append("useradd")
		cmds.append("-m")
		action = "created"
	else:
		cmds.append("usermod")
		action = "modified"
	if "uid" in cfg: cmds.extend(["-u", str(cfg["uid"])])
	if "gid" in cfg: cmds.extend(["-g", str(cfg["gid"])])
	if "home" in cfg: cmds.extend(["-d", cfg["home"]])
	if "shell" in cfg: cmds.extend(["-s", cfg["shell"]])
	if "groups" in cfg: cmds.extend(["-G", str(cfg["groups"])])
	cmds.append(name)
	ret = chroot_run(ctx, cmds)
	if ret != 0: raise OSError(f"{cmds[0]} failed")
	if "password" in cfg:
		cmds = ["chpasswd"]
		text = f"{name}:{cfg['password']}\n"
		ret = chroot_run(ctx, cmds, stdin=text)
		if ret != 0: raise OSError("chpasswd failed")
	ctx.reload_passwd()
	log.info(f"{action} user {name}")


def proc_group(ctx: ArchBuilderContext, cfg: dict):
	if "name" not in cfg: raise ArchBuilderConfigError("groupname not set")
	name = cfg["name"]
	cmds = []
	if ctx.passwd.lookup_name(name) is None:
		cmds.append("groupadd")
		action = "created"
	else:
		cmds.append("groupmod")
		action = "modified"
	if "gid" in cfg: cmds.extend(["-g", str(cfg["gid"])])
	cmds.append(name)
	ret = chroot_run(ctx, cmds)
	if ret != 0: raise OSError(f"{name} failed")
	ctx.reload_passwd()
	log.info(f"{action} group {name}")


def proc_users(ctx: ArchBuilderContext):
	for user in ctx.get("sysconf.user", []):
		proc_user(ctx, user)


def proc_groups(ctx: ArchBuilderContext):
	for group in ctx.get("sysconf.group", []):
		proc_group(ctx, group)


def proc_usergroup(ctx: ArchBuilderContext):
	proc_groups(ctx)
	proc_users(ctx)
