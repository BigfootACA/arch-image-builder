import os
from logging import getLogger
from builder.component.pacman import Pacman
from builder.lib.context import ArchBuilderContext
from builder.lib.utils import open_config
log = getLogger(__name__)


def install_all(ctx: ArchBuilderContext, pacman: Pacman):
	packages = ctx.get("pacman.install", [])
	if len(packages) <= 0: return
	log.info("installing packages: %s", " ".join(packages))
	pacman.install(packages)


def install_all_keyring(ctx: ArchBuilderContext, pacman: Pacman):
	packages: list[str] = ctx.get("pacman.install", [])
	if len(packages) <= 0: return
	keyrings = [pkg for pkg in packages if pkg.endswith("-keyring")]
	if len(keyrings) <= 0: return
	log.info("installing keyrings: %s", " ".join(keyrings))
	pacman.add_trust_keyring_pkg(keyrings)


def uninstall_all(ctx: ArchBuilderContext, pacman: Pacman):
	packages = ctx.get("pacman.uninstall", [])
	if len(packages) <= 0: return
	log.info("uninstalling packages: %s", " ".join(packages))
	pacman.uninstall(packages)


def append_config(ctx: ArchBuilderContext, lines: list[str]):
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
	conf = os.path.join(ctx.get_rootfs(), "etc/pacman.conf")
	lines: list[str] = []
	append_config(ctx, lines)
	pacman.append_repos(lines)
	with open_config(conf) as f:
		f.writelines(lines)
	log.info(f"generated pacman config {conf}")


def proc_pacman(ctx: ArchBuilderContext, pacman: Pacman):
	install_all(ctx, pacman)
	uninstall_all(ctx, pacman)
	gen_config(ctx, pacman)


def proc_pacman_keyring(ctx: ArchBuilderContext, pacman: Pacman):
	install_all_keyring(ctx, pacman)


def trust_all(ctx: ArchBuilderContext, pacman: Pacman):
	if not ctx.gpgcheck: return
	trust = ctx.get("pacman.trust", [])
	pacman.recv_keys(trust)
	for key in trust: pacman.lsign_key(key)
