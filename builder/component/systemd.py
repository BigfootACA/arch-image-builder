from builder.lib import utils
from builder.build import filesystem
from builder.lib.context import ArchBuilderContext


def systemctl(ctx: ArchBuilderContext, args: list[str]):
	"""
	Call systemctl in rootfs
	"""
	path = ctx.get_rootfs()
	full_args = ["systemctl"]
	if utils.have_external("systemctl"):
		# use host systemctl possible
		full_args.append(f"--root={path}")
		full_args.extend(args)
		ret = ctx.run_external(full_args)
	else:
		# if host systemd is unavailable, use chroot run
		full_args.extend(args)
		ret = filesystem.chroot_run(ctx, full_args)
	if ret != 0: raise OSError(
		"systemctl %s failed: %d" %
		(" ".join(args), ret)
	)


def enable(ctx: ArchBuilderContext, units: list[str]):
	"""
	Enable systemd units
	"""
	if len(units) <= 0: return
	args = ["enable", "--"]
	args.extend(units)
	systemctl(ctx, args)


def disable(ctx: ArchBuilderContext, units: list[str]):
	"""
	Disable systemd units
	"""
	if len(units) <= 0: return
	args = ["disable", "--"]
	args.extend(units)
	systemctl(ctx, args)


def set_default(ctx: ArchBuilderContext, unit: str):
	"""
	Set default boot target for systemd
	"""
	if not unit: return
	systemctl(ctx, ["set-default", "--", unit])
