import os
from logging import getLogger
from builder.component.pacman import Pacman
from builder.lib.context import ArchBuilderContext
from builder.lib.utils import open_config
log = getLogger(__name__)


def install_all(ctx: ArchBuilderContext, pacman: Pacman):
	"""
	Install all pacman packages
	"""
	packages = ctx.get("pacman.install", [])
	if len(packages) <= 0: return
	log.info("installing packages: %s", " ".join(packages))
	pacman.install(packages)


def install_all_keyring(ctx: ArchBuilderContext, pacman: Pacman):
	"""
	Install all pacman keyring packages before normal packages
	"""
	packages: list[str] = ctx.get("pacman.install", [])
	if len(packages) <= 0: return

	# find out all keyring packages
	keyrings = [pkg for pkg in packages if pkg.endswith("-keyring")]
	if len(keyrings) <= 0: return

	log.info("installing keyrings: %s", " ".join(keyrings))
	pacman.add_trust_keyring_pkg(keyrings, nogpg=True)


def uninstall_all(ctx: ArchBuilderContext, pacman: Pacman):
	"""
	Remove all specified pacman packages
	"""
	packages = ctx.get("pacman.uninstall", [])
	if len(packages) <= 0: return
	log.info("uninstalling packages: %s", " ".join(packages))
	pacman.uninstall(packages)


def append_config(ctx: ArchBuilderContext, lines: list[str]):
	"""
	Generate basic pacman.conf for rootfs
	"""
	lines.append("[options]\n")
	lines.append("HoldPkg = pacman glibc filesystem\n")
	lines.append(f"Architecture = {ctx.tgt_arch}\n")
	lines.append("UseSyslog\n")
	lines.append("Color\n")
	lines.append("CheckSpace\n")
	lines.append("VerbosePkgLists\n")
	lines.append("ParallelDownloads = 5\n")
	lines.append("SigLevel = Required DatabaseOptional\n")
	lines.append("LocalFileSigLevel = Optional\n")


def gen_config(ctx: ArchBuilderContext, pacman: Pacman):
	"""
	Generate full pacman.conf for rootfs
	"""
	conf = os.path.join(ctx.get_rootfs(), "etc/pacman.conf")
	lines: list[str] = []
	append_config(ctx, lines)
	pacman.append_repos(lines, True)
	with open_config(conf) as f:
		f.writelines(lines)
	log.info(f"generated pacman config {conf}")


def gen_mirrorlist(ctx: ArchBuilderContext, pacman: Pacman):
	conf = os.path.join(ctx.get_rootfs(), "etc/pacman.d/mirrorlist")
	lines: list[str] = []
	pacman.append_mirrorlist(lines)
	with open_config(conf) as f:
		f.writelines(lines)
	log.info(f"generated pacman mirrorlist {conf}")


def proc_pacman(ctx: ArchBuilderContext, pacman: Pacman):
	"""
	Install or remove packages for rootfs, and generate pacman.conf
	"""
	install_all(ctx, pacman)
	uninstall_all(ctx, pacman)
	gen_config(ctx, pacman)
	if ctx.get("pacman.gen_mirrorlist", True):
		gen_mirrorlist(ctx, pacman)


def proc_pacman_keyring(ctx: ArchBuilderContext, pacman: Pacman):
	"""
	Early install keyring packages
	"""
	install_all_keyring(ctx, pacman)


def trust_all(ctx: ArchBuilderContext, pacman: Pacman, fail: bool=False):
	"""
	Early trust keyring for database and keyring packages
	"""
	if not ctx.gpgcheck: return
	trust = ctx.get("pacman.trust", [])

	# receive all keys now
	try: pacman.pacman_key.recv_keys(trust)
	except: log.warning("recv-keys partial failed")

	# local sign keys
	for key in trust:
		try:
			pacman.pacman_key.lsign_key(key)
		except:
			if not fail: raise
			log.warning(f"lsign-key {key} failed")
