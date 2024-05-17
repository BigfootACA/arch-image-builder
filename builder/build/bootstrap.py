import os
import shutil
from logging import getLogger
from builder.disk import image
from builder.build import mount, fstab, grub, user, filesystem
from builder.build import locale, systemd, mkinitcpio, names
from builder.build import pacman as pacman_build
from builder.component import pacman as pacman_comp
from builder.lib.context import ArchBuilderContext
log = getLogger(__name__)


def cleanup(ctx: ArchBuilderContext):
	"""
	Cleanup unneeded files for Arch Linux
	"""
	root = ctx.get_rootfs()

	def rm_rf(path: str):
		real = os.path.join(root, path)
		if not os.path.exists(real): return
		shutil.rmtree(real, True)

	def del_child(path: str, prefix: str = None, suffix: str = None):
		real = os.path.join(root, path)
		if not os.path.exists(real): return
		for file in os.listdir(real):
			if prefix and not file.startswith(prefix): continue
			if suffix and not file.endswith(suffix): continue
			rm_rf(os.path.join(real, file))
	rm_rf("var/log/pacman.log")
	del_child("var/cache/pacman/pkg")
	del_child("var/lib/pacman/sync")
	del_child("etc", suffix="-")
	rm_rf("etc/.pwd.lock")


def do_copy(ctx: ArchBuilderContext, src: str, dst: str):
	"""
	Copying rootfs via rsync
	"""
	rsrc = os.path.realpath(src)
	rdst = os.path.realpath(dst)
	log.info("start copying rootfs...")
	ret = ctx.run_external([
		"rsync", "--archive", "--recursive",
		"--delete", "--info=progress2",
		rsrc + os.sep, rdst
	])
	os.sync()
	if ret != 0: raise OSError("rsync failed")


def build_rootfs(ctx: ArchBuilderContext):
	"""
	Build whole rootfs and generate image
	"""
	log.info("building rootfs")

	# create folders
	os.makedirs(ctx.work, mode=0o755, exist_ok=True)
	os.makedirs(ctx.get_rootfs(), mode=0o0755, exist_ok=True)
	os.makedirs(ctx.get_output(), mode=0o0755, exist_ok=True)
	os.makedirs(ctx.get_mount(), mode=0o0755, exist_ok=True)

	# build rootfs contents
	if not ctx.repack:
		try:
			# initialize basic folders
			mount.init_rootfs(ctx)

			# initialize mount points for chroot
			mount.init_mount(ctx)

			# initialize pacman context
			pacman = pacman_comp.Pacman(ctx)

			# initialize build time keyring
			pacman.init_keyring()

			# trust pgp key in config (for pacman database)
			pacman_build.trust_all(ctx, pacman)

			# update pacman repos databases
			pacman.load_databases()

			# install all keyring packages before other packages
			pacman_build.proc_pacman_keyring(ctx, pacman)

			# real install all packages
			pacman_build.proc_pacman(ctx, pacman)

			# reload user databases after install packages
			ctx.reload_passwd()

			# create custom users and groups
			user.proc_usergroup(ctx)

			# build time files add/remove hooks
			filesystem.proc_filesystem(ctx)

			# enable / disable systemd units
			systemd.proc_systemd(ctx)

			# setup locale (timezone / i18n language / fonts / input methods)
			locale.proc_locale(ctx)

			# setup system names (environments / hosts / hostname / machine-info)
			names.proc_names(ctx)

			# recreate initramfs
			mkinitcpio.proc_mkinitcpio(ctx)

			# reset machine-id (never duplicated machine id)
			systemd.proc_machine_id(ctx)
		finally:
			# kill spawned daemons (gpg-agent, dirmngr, ...)
			ctx.cgroup.kill_all()

			# remove mount points
			mount.undo_mounts(ctx)

		# cleanup unneeded files
		cleanup(ctx)

	# reload user database before create images
	ctx.reload_passwd()

	# create images and initialize bootloader
	try:
		# create disk and filesystem image
		image.proc_image(ctx)

		# generate fstab
		fstab.proc_fstab(ctx)

		# install grub bootloader
		grub.proc_grub(ctx)

		# running add files hooks (for bootloader settings)
		filesystem.add_files_all(ctx, "post-fs")

		# copy rootfs into image
		do_copy(ctx, ctx.get_rootfs(), ctx.get_mount())
	finally:
		ctx.cleanup()

	# finish
	log.info("build done!")
	os.sync()
	log.info(f"your images are in {ctx.get_output()}")
	ctx.run_external(["ls", "-lh", ctx.get_output()])
