import os
import pyalpm
import logging
import shutil
import libarchive
from logging import getLogger
from builder.lib.context import ArchBuilderContext
from builder.lib.config import ArchBuilderConfigError
log = getLogger(__name__)


def log_cb(level, line):
	if level & pyalpm.LOG_ERROR:
		ll = logging.ERROR
	elif level & pyalpm.LOG_WARNING:
		ll = logging.WARNING
	else: return
	log.log(ll, line.strip())


def dl_cb(filename, ev, data):
	match ev:
		case 0: log.debug(f"pacman downloading {filename}")
		case 2: log.warning(f"pacman retry download {filename}")
		case 3: log.info(f"pacman downloaded {filename}")


def progress_cb(target, percent, n, i):
	if len(target) <= 0 or percent != 0: return
	log.info(f"processing {target} ({i}/{n})")


class Pacman:
	handle: pyalpm.Handle
	ctx: ArchBuilderContext
	root: str
	databases: dict[str: pyalpm.DB]
	config: dict
	caches: list[str]

	def append_repos(self, lines: list[str]):
		for repo in self.databases:
			db = self.databases[repo]
			lines.append(f"[{repo}]\n")
			for server in db.servers:
				log.debug(f"server {server}")
				lines.append(f"Server = {server}\n")

	def append_config(self, lines: list[str]):
		siglevel = ("Required DatabaseOptional" if self.ctx.gpgcheck else "Never")
		lines.append("[options]\n")
		for cache in self.caches:
			lines.append(f"CacheDir = {cache}\n")
		lines.append(f"RootDir = {self.root}\n")
		lines.append(f"GPGDir = {self.handle.gpgdir}\n")
		lines.append(f"LogFile = {self.handle.logfile}\n")
		lines.append("HoldPkg = pacman glibc\n")
		lines.append(f"Architecture = {self.ctx.tgt_arch}\n")
		lines.append("UseSyslog\n")
		lines.append("Color\n")
		lines.append("CheckSpace\n")
		lines.append("VerbosePkgLists\n")
		lines.append("ParallelDownloads = 5\n")
		lines.append(f"SigLevel = {siglevel}\n")
		lines.append("LocalFileSigLevel = Optional\n")
		self.append_repos(lines)

	def init_keyring(self):
		path = os.path.join(self.ctx.work, "rootfs")
		keyring = os.path.join(path, "etc/pacman.d/gnupg")
		if not self.ctx.gpgcheck: return
		if os.path.exists(os.path.join(keyring, "trustdb.gpg")):
			log.debug("skip initialize pacman keyring when exists")
			return
		log.info("initializing pacman keyring")
		self.pacman_key(["--init"])

	def init_config(self):
		config = os.path.join(self.ctx.work, "pacman.conf")
		if os.path.exists(config):
			os.remove(config)
		log.info(f"generate pacman config {config}")
		lines = []
		self.append_config(lines)
		log.debug("config content: %s", "\t".join(lines).strip())
		log.debug(f"writing {config}")
		with open(config, "w") as f:
			f.writelines(lines)

	def pacman_key(self, args: list[str]):
		if not self.ctx.gpgcheck:
			raise RuntimeError("GPG check disabled")
		keyring = os.path.join(self.root, "etc/pacman.d/gnupg")
		config = os.path.join(self.ctx.work, "pacman.conf")
		cmds = ["pacman-key"]
		cmds.append(f"--gpgdir={keyring}")
		cmds.append(f"--config={config}")
		cmds.extend(args)
		ret = self.ctx.run_external(cmds)
		if ret != 0: raise OSError(f"pacman-key failed with {ret}")

	def pacman(self, args: list[str]):
		config = os.path.join(self.ctx.work, "pacman.conf")
		cmds = ["pacman"]
		cmds.append("--noconfirm")
		cmds.append(f"--root={self.root}")
		cmds.append(f"--config={config}")
		cmds.extend(args)
		ret = self.ctx.run_external(cmds)
		if ret != 0: raise OSError(f"pacman failed with {ret}")

	def add_database(self, repo: dict):
		def resolve(url: str) -> str:
			return (url
				.replace("$arch", self.ctx.tgt_arch)
				.replace("$repo", name))
		if "name" not in repo:
			raise ArchBuilderConfigError("repo name not set")
		name = repo["name"]
		if name == "local" or "/" in name:
			raise ArchBuilderConfigError("bad repo name")
		if name not in self.databases:
			self.databases[name] = self.handle.register_syncdb(
				name, pyalpm.SIG_DATABASE_MARGINAL_OK
			)
		db = self.databases[name]
		servers: list[str] = []
		if "server" in repo:
			servers.append(resolve(repo["server"]))
		if "servers" in repo:
			for server in repo["servers"]:
				servers.append(resolve(server))
		db.servers = servers
		log.info(f"updating database {name}")
		db.update(False)

	def load_databases(self):
		cfg = self.config
		if "repo" not in cfg:
			raise ArchBuilderConfigError("no repos found in config")
		for repo in cfg["repo"]:
			self.add_database(repo)
		self.init_config()
		self.refresh()

	def lookup_package(self, name: str) -> list[pyalpm.Package]:
		if ".pkg.tar." in name:
			pkg = self.handle.load_pkg(name)
			if pkg is None: raise RuntimeError(f"load package {name} failed")
			return [pkg]
		s = name.split("/")
		if len(s) == 2:
			if s[0] not in self.databases:
				raise ValueError(f"database {s[0]} not found")
			db = (self.handle.get_localdb() if s[0] == "local" else self.databases[s[0]])
			pkg = db.get_pkg(s[1])
			if pkg: return [pkg]
			raise ValueError(f"package {s[1]} not found")
		elif len(s) == 1:
			pkg = pyalpm.find_grp_pkgs(self.databases.values(), name)
			if len(pkg) > 0: return pkg
			for dbn in self.databases:
				db = self.databases[dbn]
				pkg = db.get_pkg(name)
				if pkg: return [pkg]
			raise ValueError(f"package {name} not found")
		raise ValueError(f"bad package name {name}")

	def init_cache(self):
		host_cache = "/var/cache/pacman/pkg"
		work_cache = os.path.join(self.ctx.work, "packages")
		root_cache = os.path.join(self.root, "var/cache/pacman/pkg")
		self.caches.clear()
		if os.path.exists(host_cache):
			self.caches.append(host_cache)
		self.caches.append(work_cache)
		self.caches.append(root_cache)
		os.makedirs(work_cache, mode=0o0755, exist_ok=True)
		os.makedirs(root_cache, mode=0o0755, exist_ok=True)

	def __init__(self, ctx: ArchBuilderContext):
		self.ctx = ctx
		if "pacman" not in ctx.config:
			raise ArchBuilderConfigError("no pacman found in config")
		self.config = ctx.config["pacman"]
		self.root = ctx.get_rootfs()
		db = os.path.join(self.root, "var/lib/pacman")
		self.handle = pyalpm.Handle(self.root, db)
		self.handle.arch = ctx.tgt_arch
		self.handle.logfile = os.path.join(self.ctx.work, "pacman.log")
		self.handle.gpgdir = os.path.join(self.root, "etc/pacman.d/gnupg")
		self.handle.logcb = log_cb
		self.handle.dlcb = dl_cb
		self.handle.progresscb = progress_cb
		self.databases = {}
		self.caches = []
		self.init_cache()
		for cache in self.caches:
			self.handle.add_cachedir(cache)
		self.init_config()

	def uninstall(self, pkgs: list[str]):
		if len(pkgs) == 0: return
		ps = " ".join(pkgs)
		log.info(f"removing packages {ps}")
		args = ["--needed", "--remove"]
		args.extend(pkgs)
		self.pacman(args)

	def install(
		self,
		pkgs: list[str],
		/,
		force: bool = False,
		asdeps: bool = False,
		nodeps: bool = False,
	):
		if len(pkgs) == 0: return
		core_db = "var/lib/pacman/sync/core.db"
		if not os.path.exists(os.path.join(self.root, core_db)):
			self.refresh()
		ps = " ".join(pkgs)
		log.info(f"installing packages {ps}")
		args = ["--sync"]
		if not force: args.append("--needed")
		if asdeps: args.append("--asdeps")
		if nodeps: args.extend(["--nodeps", "--nodeps"])
		args.extend(pkgs)
		self.pacman(args)

	def download(self, pkgs: list[str]):
		if len(pkgs) == 0: return
		core_db = "var/lib/pacman/sync/core.db"
		if not os.path.exists(os.path.join(self.root, core_db)):
			self.refresh()
		log.info("downloading packages %s", " ".join(pkgs))
		args = ["--sync", "--downloadonly", "--nodeps", "--nodeps"]
		args.extend(pkgs)
		self.pacman(args)

	def install_local(self, files: list[str]):
		if len(files) == 0: return
		log.info("installing local packages %s", " ".join(files))
		args = ["--needed", "--upgrade"]
		args.extend(files)
		self.pacman(args)

	def refresh(self, /, force: bool = False):
		log.info("refresh pacman database")
		args = ["--sync", "--refresh"]
		if force: args.append("--refresh")
		self.pacman(args)

	def recv_keys(self, keys: str | list[str]):
		args = ["--recv-keys"]
		if type(keys) is str:
			args.append(keys)
		elif type(keys) is list:
			if len(keys) <= 0: return
			args.extend(keys)
		else: raise TypeError("bad keys type")
		self.pacman_key(args)

	def lsign_key(self, key: str):
		self.pacman_key(["--lsign-key", key])

	def pouplate_keys(
		self,
		names: str | list[str] = None,
		folder: str = None
	):
		args = ["--populate"]
		if folder: args.extend(["--populate-from", folder])
		if names is None: pass
		elif type(names) is str: args.append(names)
		elif type(names) is list: args.extend(names)
		else: raise TypeError("bad names type")
		self.pacman_key(args)

	def find_package_file(self, pkg: pyalpm.Package) -> str | None:
		for cache in self.caches:
			p = os.path.join(cache, pkg.filename)
			if os.path.exists(p): return p
		return None

	def trust_keyring_pkg(self, pkg: pyalpm.Package):
		if not self.ctx.gpgcheck: return
		names: list[str] = []
		target = os.path.join(self.ctx.work, "keyrings")
		keyring = "usr/share/pacman/keyrings/"
		path = self.find_package_file(pkg)
		if os.path.exists(target):
			shutil.rmtree(target)
		os.makedirs(target, mode=0o0755)
		if path is None: raise RuntimeError(
			f"package {pkg.name} not found"
		)
		log.debug(f"processing keyring package {pkg.name}")
		with libarchive.file_reader(path) as archive:
			for file in archive:
				pn: str = file.pathname
				if not pn.startswith(keyring): continue
				fn = pn[len(keyring):]
				if len(fn) <= 0: continue
				if fn.endswith(".gpg"): names.append(fn[:-4])
				dest = os.path.join(target, fn)
				log.debug(f"extracting {pn} to {dest}")
				with open(dest, "wb") as f:
					for block in file.get_blocks(file.size):
						f.write(block)
					fd = f.fileno()
					os.fchmod(fd, file.mode)
					os.fchown(fd, file.uid, file.gid)
		self.pouplate_keys(names, target)

	def add_trust_keyring_pkg(self, pkgnames: list[str]):
		if not self.ctx.gpgcheck: return
		if len(pkgnames) <= 0: return
		self.download(pkgnames)
		for pkgname in pkgnames:
			pkgs = self.lookup_package(pkgname)
			for pkg in pkgs:
				self.trust_keyring_pkg(pkg)
