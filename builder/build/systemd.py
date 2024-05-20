import os
from logging import getLogger
from builder.lib.context import ArchBuilderContext
from builder.component import systemd as systemd_comp
log = getLogger(__name__)


def proc_systemd(ctx: ArchBuilderContext):
	"""
	Enable or disable systemd units files, and set default target
	"""
	systemd_comp.enable(ctx, ctx.get("systemd.enable", []))
	systemd_comp.disable(ctx, ctx.get("systemd.disable", []))
	systemd_comp.set_default(ctx, ctx.get("systemd.default", None))


def proc_machine_id(ctx: ArchBuilderContext):
	"""
	Remove or set machine-id
	Never duplicate machine id, it should generate when first boot
	"""
	id = ctx.get("machine-id", "")
	root = ctx.get_rootfs()
	mid = os.path.join(root, "etc/machine-id")
	with open(mid, "w") as f:
		f.write(id)
		f.write(os.linesep)
	if len(id) == 0: log.info("removed machine-id")
	else: log.info(f"set machine-id to {id}")
