import os
from logging import getLogger
from builder.lib.context import ArchBuilderContext
from builder.lib.config import ArchBuilderConfigError
from builder.lib.utils import open_config
log = getLogger(__name__)


def gen_machine_info(ctx: ArchBuilderContext):
	root = ctx.get_rootfs()
	file = os.path.join(root, "etc/machine-info")
	cfg = ctx.get("sysconf")
	fields = [
		"chassis", "location", "icon_name",
		"deployment", "pretty_hostname"
	]
	with open_config(file) as f:
		for field in fields:
			if field not in cfg: continue
			f.write("%s=\"%s\"\n" % (field.upper(), cfg[field]))
	log.info(f"generated machine-info {file}")


def gen_hosts(ctx: ArchBuilderContext):
	addrs: list[str] = []
	root = ctx.get_rootfs()
	file = os.path.join(root, "etc/hosts")
	hosts: list[str] = ctx.get("sysconf.hosts", [])
	with open_config(file) as f:
		for addr in hosts:
			s = addr.split()
			if len(s) <= 1: raise ArchBuilderConfigError("bad host entry")
			addrs.append(s[0])
			f.write(addr)
			f.write(os.linesep)
		name = ctx.get("sysconf.hostname")
		if "127.0.1.1" not in addrs and name:
			f.write(f"127.0.1.1 {name}\n")
	log.info(f"generated hosts {file}")


def gen_hostname(ctx: ArchBuilderContext):
	root = ctx.get_rootfs()
	file = os.path.join(root, "etc/hostname")
	name = ctx.get("sysconf.hostname")
	if name is None: return
	with open_config(file) as f:
		f.write(name)
		f.write(os.linesep)
	log.info(f"generated hostname {file}")


def gen_environments(ctx: ArchBuilderContext):
	root = ctx.get_rootfs()
	file = os.path.join(root, "etc/environment")
	envs: dict[str] = ctx.get("sysconf.environments", [])
	with open_config(file) as f:
		for key in envs:
			val = envs[key]
			f.write(f"{key}=\"{val}\"\n")
	log.info(f"generated environment {file}")


def proc_names(ctx: ArchBuilderContext):
	gen_machine_info(ctx)
	gen_environments(ctx)
	gen_hostname(ctx)
	gen_hosts(ctx)
