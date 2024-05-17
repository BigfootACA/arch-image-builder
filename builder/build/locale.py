import os
from logging import getLogger
from builder.build import filesystem
from builder.lib.context import ArchBuilderContext
from builder.lib.config import ArchBuilderConfigError
from builder.lib.utils import open_config
log = getLogger(__name__)


def reset_locale(ctx: ArchBuilderContext):
	root = ctx.get_rootfs()
	archive = os.path.join(root, "usr/lib/locale/locale-archive")
	if os.path.exists(archive): os.remove(archive)


def enable_all(ctx: ArchBuilderContext):
	root = ctx.get_rootfs()
	locales = ctx.get("locale.enable", [])
	log.info("setup enabled locale")
	file = os.path.join(root, "etc/locale.gen")
	with open_config(file) as f:
		for line in locales:
			log.debug(f"adding locale {line}")
			f.write(line)
			f.write("\n")
		if len(locales) == 0:
			f.write("# No any locales enabled\n")
	filesystem.chroot_run(ctx, "locale-gen")


def set_default(ctx: ArchBuilderContext):
	root = ctx.get_rootfs()
	default = ctx.get("locale.default", None)
	if default is None: default = "C"
	log.info(f"default locale: {default}")
	conf = os.path.join(root, "etc/locale.conf")
	with open_config(conf) as f:
		f.write(f"LANG={default}\n")


def set_timezone(ctx: ArchBuilderContext):
	root = ctx.get_rootfs()
	timezone = ctx.get("timezone", None)
	if timezone is None: timezone = "UTC"
	log.info(f"timezone: {timezone}")
	dst = os.path.join("/usr/share/zoneinfo", timezone)
	real = os.path.join(root, dst[1:])
	if not os.path.exists(real): raise ArchBuilderConfigError(
		f"timezone {timezone} not found"
	)
	lnk = os.path.join(root, "etc/localtime")
	if os.path.exists(lnk): os.remove(lnk)
	os.symlink(dst, lnk)
	conf = os.path.join(root, "etc/timezone")
	with open(conf, "w") as f:
		f.write(timezone)
		f.write(os.linesep)


def proc_locale(ctx: ArchBuilderContext):
	reset_locale(ctx)
	enable_all(ctx)
	set_default(ctx)
	set_timezone(ctx)
