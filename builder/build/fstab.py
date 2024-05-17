import os
from logging import getLogger
from builder.lib.context import ArchBuilderContext
from builder.lib.utils import open_config
log = getLogger(__name__)


def write_fstab(ctx: ArchBuilderContext):
	log.debug(
		"generate fstab:\n\t%s",
		ctx.fstab.to_mount_file("\n\t").strip()
	)
	path = os.path.join(ctx.get_rootfs(), "etc/fstab")
	with open_config(path) as f:
		ctx.fstab.write_mount_file(f)


def mount_all(ctx: ArchBuilderContext):
	path = ctx.get_mount()
	root = ctx.get_rootfs()
	if not os.path.exists(path):
		os.mkdir(path, mode=0o0755)
	if ctx.fstab[0].target != "/":
		raise RuntimeError("no root to mount")
	for mnt in ctx.fstab:
		m = mnt.clone()
		if m.source == "none": continue
		if m.source not in ctx.fsmap:
			raise RuntimeError(f"source {m.source} cannot map to host")
		m.source = ctx.fsmap[m.source]
		if m.target == "/": in_mnt, in_root = path, root
		elif m.target.startswith("/"):
			folder = m.target[1:]
			in_mnt = os.path.join(path, folder)
			in_root = os.path.join(root, folder)
		elif m.fstype == "swap" or m.target == "none": continue
		else: raise RuntimeError(f"target {m.target} cannot map to host")
		if in_mnt:
			m.target = in_mnt
			if not os.path.exists(in_mnt):
				os.makedirs(in_mnt, mode=0o0755)
		if in_root and not os.path.exists(in_root):
			os.makedirs(in_root, mode=0o0755)
		m.mount()
		ctx.mounted.insert(0, m)


def proc_fstab(ctx: ArchBuilderContext):
	ctx.fstab.resort()
	write_fstab(ctx)
	mount_all(ctx)
