import os
from logging import getLogger
from builder.lib.context import ArchBuilderContext
from builder.lib.utils import open_config
log = getLogger(__name__)


def write_fstab(ctx: ArchBuilderContext):
	"""
	Generate fstab and write to rootfs
	"""
	log.debug(
		"generate fstab:\n\t%s",
		ctx.fstab.to_mount_file("\n\t").strip()
	)
	# WORKSPACE/TARGET/rootfs/etc/fstab
	path = os.path.join(ctx.get_rootfs(), "etc/fstab")
	with open_config(path) as f:
		ctx.fstab.write_mount_file(f)


def mount_all(ctx: ArchBuilderContext):
	"""
	Mount all filesystems in fstab for build
	"""
	path = ctx.get_mount()
	root = ctx.get_rootfs()

	# ensure WORKSPACE/TARGET/mount is existing
	if not os.path.exists(path):
		os.mkdir(path, mode=0o0755)

	# the first item must be ROOT (sorted by ctx.fstab.resort())
	if ctx.fstab[0].target != "/":
		raise RuntimeError("no root to mount")

	for mnt in ctx.fstab:
		# do not change original item
		m = mnt.clone()

		# skip virtual source device
		if m.source == "none": continue

		# we should mount virtual device
		# original: /dev/mmcblk0p1, PARTLABEL=linux
		# we need: /dev/loop0, /dev/loop1
		# see builder.disk.filesystem.build.FileSystemBuilder.proc_fstab()
		if m.source not in ctx.fsmap:
			raise RuntimeError(f"source {m.source} cannot map to host")
		m.source = ctx.fsmap[m.source]

		if m.target == "/":
			# process ROOT resolve unneeded
			in_mnt, in_root = path, root
		elif m.target.startswith("/"):
			# resolve to ROOT and MOUNT
			# m.target: /boot
			# in_mnt: WORKSPACE/TARGET/mount/boot
			# in_root: WORKSPACE/TARGET/rootfs/boot
			folder = m.target[1:]
			in_mnt = os.path.join(path, folder)
			in_root = os.path.join(root, folder)
		elif m.fstype == "swap" or m.target == "none":
			# skip mount virtual fs and swap
			continue
		else: raise RuntimeError(f"target {m.target} cannot map to host")

		if in_mnt:
			# ensure mount target is exists
			m.target = in_mnt
			if not os.path.exists(in_mnt):
				os.makedirs(in_mnt, mode=0o0755)
		if in_root and not os.path.exists(in_root):
			# ensure the folder is also exists in rootfs
			os.makedirs(in_root, mode=0o0755)

		# invoke real mount
		m.mount()
		ctx.mounted.insert(0, m)


def proc_fstab(ctx: ArchBuilderContext):
	ctx.fstab.resort()
	write_fstab(ctx)
	mount_all(ctx)
