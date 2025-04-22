import os
import pyalpm
import logging
import shutil
import libarchive
from logging import getLogger
from builder.lib.serializable import SerializableDict
from builder.lib.context import ArchBuilderContext
from builder.lib.config import ArchBuilderConfigError
from builder.lib.subscript import resolve_simple_values
from builder.component.pacman_key import PacmanKey
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


class PacmanRepoServer(SerializableDict):
	ctx: ArchBuilderContext
	url: str = None
	config_url: str = None
	name: str = None
	mirror: bool = False

	def __init__(
		self,
		ctx: ArchBuilderContext,
		name: str = None,
		url: str = None,
		config_url: str = None,
		mirror: bool = None
	):
		self.ctx = ctx
		if url is not None: self.url = url
		if config_url is not None: self.config_url = config_url
		if name is not None: self.name = name
		if mirror is not None: self.mirror = mirror

	def append_server(self, lines: list[str]):
		if self.mirror:
			lines.append(f"# Mirror {self.name}\n")
			log.debug(f"use mirror {self.name} url {self.config_url}")
		else:
			lines.append("# Original Repo\n")
			log.debug(f"use original repo url {self.config_url}")
		for _ in range(self.ctx.retry_count):
			lines.append(f"Server = {self.config_url}\n")

class PacmanRepo(SerializableDict):
	ctx: ArchBuilderContext
	name: str = None
	priority: int = 10000
	servers: list[PacmanRepoServer] = None
	mirrorlist: str = None
	publickey: str = None
	keyid: str = None

	def __init__(
		self,
		ctx: ArchBuilderContext,
		name: str = None,
		priority: int = None,
		servers: list[PacmanRepoServer] = None,
		mirrorlist: str = None,
		publickey: str = None,
		keyid: str = None
	):
		self.ctx = ctx
		if name is not None: self.name = name
		if priority is not None: self.priority = priority
		if servers is not None: self.servers = servers
		else: self.servers = []
		if mirrorlist is not None: self.mirrorlist = mirrorlist
		if publickey is not None: self.publickey = publickey
		if keyid is not None: self.keyid = keyid

	def add_server(
		self,
		name: str = None,
		url: str = None,
		config_url: str = None,
		mirror: bool = None
	):
		self.servers.append(PacmanRepoServer(
			ctx=self.ctx,
			name=name,
			url=url,
			config_url=config_url,
			mirror=mirror,
		))

	def append_repo(self, lines: list[str]):
		for server in self.servers:
			server.append_server(lines)


def is_remote(val: str) -> bool:
	if not val: return False
	if val.startswith("http://"): return True
	if val.startswith("https://"): return True
	return False


class Pacman:
	handle: pyalpm.Handle
	ctx: ArchBuilderContext
	root: str
	databases: dict[str: pyalpm.DB]
	config: dict
	caches: list[str]
	repos: list[PacmanRepo]
	package_map: dict[str: str] = None

	def append_repos(self, lines: list[str], rootfs: bool = False):
		"""
		Add all databases into config
		"""
		for repo in self.repos:
			lines.append(f"[{repo.name}]\n")
			if rootfs and repo.mirrorlist:
				if is_remote(repo.mirrorlist):
					lines.append(f"Include = /etc/pacman.d/{repo.name}-mirrorlist\n")
					continue
				elif repo.mirrorlist == "default":
					lines.append("Include = /etc/pacman.d/mirrorlist\n")
					continue
				elif repo.mirrorlist.startswith("/"):
					lines.append(f"Include = {repo.mirrorlist}\n")
					continue
				elif repo.mirrorlist.startswith("distro:"):
					dist = self.ctx.get("distro.id", None)
					matches = repo.mirrorlist[7:].split(",")
					if dist and matches and dist in matches:
						lines.append("Include = /etc/pacman.d/mirrorlist\n")
						continue
				else: raise ArchBuilderConfigError(
					f"unknown value {repo.mirrorlist} for mirrorlist"
				)
			repo.append_repo(lines)			

	def append_mirrorlist(self, lines: list[str]):
		servers: list[PacmanRepoServer] = []
		for repo in self.repos:
			for server in repo.servers:
				if not any((server.name == local.name for local in servers)):
					servers.append(server)
		for server in servers:
			server.append_server(lines)

	def append_config(self, lines: list[str]):
		"""
		Add basic pacman config for host
		"""
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
		"""
		Initialize pacman keyring
		"""
		path = os.path.join(self.ctx.work, "rootfs")
		keyring = os.path.join(path, "etc/pacman.d/gnupg")
		if not self.ctx.gpgcheck: return
		if os.path.exists(os.path.join(keyring, "trustdb.gpg")):
			log.debug("skip initialize pacman keyring when exists")
			return
		log.info("initializing pacman keyring")
		self.pacman_key.initialize()

		# Download and add public keys and mirrorlist
		for repo in self.repos:
			if is_remote(repo.mirrorlist):
				mirrorlist = os.path.join(self.ctx.work, f"etc/pacman.d/{repo.name}-mirrorlist")
				cmds = ["wget", repo.mirrorlist, "-O", mirrorlist]
				ret = self.ctx.run_external(cmds)
				if ret != 0: raise OSError(f"wget failed with {ret}")
			if repo.publickey is not None:
				keypath = os.path.join(self.ctx.work, f"{repo.name}.pub")
				cmds = ["wget", repo.publickey, "-O", keypath]
				ret = self.ctx.run_external(cmds)
				if ret != 0: raise OSError(f"wget failed with {ret}")
				self.pacman_key.add_keys_from(keypath)
				self.lsign_key(repo.keyid)
			elif repo.keyid is not None:
				self.pacman_key.recv_keys(repo.keyid)
				self.pacman_key.lsign_key(repo.keyid)

	def write_config(self, name: str, lines: list[str]) -> str:
		config = os.path.join(self.ctx.work, name)
		if os.path.exists(config):
			os.remove(config)
		log.info(f"generate pacman config {config}")
		log.debug("config content: %s", "\t".join(lines).strip())
		log.debug(f"writing {config}")
		with open(config, "w") as f:
			f.writelines(lines)
		return config

	def init_config(self):
		"""
		Create host pacman.conf and pacman-nogpg.conf
		"""
		lines_main = []
		self.append_config(lines_main)
		config_main = self.write_config("pacman.conf", lines_main)
		lines_nogpg = [
			f"Include = {config_main}\n",
			"[options]\n",
			"SigLevel = Never\n"
		]
		self.write_config("pacman-nogpg.conf", lines_nogpg)

	def pacman(self, args: list[str], nogpg: bool=False):
		"""
		Call pacman for rootfs
		"""
		config_name = "pacman-nogpg.conf" if nogpg else "pacman.conf"
		config = os.path.join(self.ctx.work, config_name)
		cmds = ["pacman"]
		cmds.append("--noconfirm")
		cmds.append(f"--root={self.root}")
		cmds.append(f"--config={config}")
		cmds.extend(args)
		ret = self.ctx.run_external(cmds)
		if ret != 0: raise OSError(f"pacman failed with {ret}")

	def load_databases(self):
		"""
		Add all databases and load them
		"""
		for mirror in self.repos:
			# register database
			if mirror.name not in self.databases:
				self.databases[mirror.name] = self.handle.register_syncdb(
					mirror.name, pyalpm.SIG_DATABASE_MARGINAL_OK
				)
			db = self.databases[mirror.name]

			# add databases servers
			servers: list[str] = []
			for server in mirror.servers:
				servers.append(server.url)
			db.servers = servers

			tries = 0
			while True:
				try:
					# update database now via pyalpm
					log.info(f"updating database {mirror.name}")
					db.update(False)
					break
				except:
					if tries < self.ctx.retry_count:
						log.warning("update database failed, retry...", exc_info=True)
						tries += 1
						continue
					raise
		self.init_config()
		self.refresh()

	def lookup_package(self, name: str, map: bool=False) -> list[pyalpm.Package]:
		"""
		Lookup pyalpm package by name
		"""

		# pass a filename, load it directly
		if ".pkg.tar." in name:
			pkg = self.handle.load_pkg(name)
			if pkg is None: raise RuntimeError(f"load package {name} failed")
			return [pkg]

		s = name.split("/")
		if len(s) == 2:
			# use DATABASE/PACKAGE, find it in database
			if s[0] not in self.databases and s[0] != "local":
				raise ValueError(f"database {s[0]} not found")
			db = (self.handle.get_localdb() if s[0] == "local" else self.databases[s[0]])
			name = s[1]
			pkg = db.get_pkg(name)
			if pkg: return [pkg]
		elif len(s) == 1:
			# use PACKAGE, find it in all databases or find as group
			pkgs = []

			# try find it as group
			pkg = pyalpm.find_grp_pkgs(self.databases.values(), name)
			if len(pkg) > 0: pkgs.extend(pkg)

			# try find it as package
			for dbn in self.databases:
				db = self.databases[dbn]
				pkg = db.get_pkg(name)
				if pkg: pkgs.append(pkg)
			if len(pkgs) > 0: return pkgs

		# package provides
		if not map:
			if name in self.package_map:
				pkg = self.package_map[name]
				return self.lookup_package(pkg, map=True)
			for dbn in self.databases:
				db = self.databases[dbn]
				pkg = pyalpm.find_satisfier(db.pkgcache, name)
				if not pkg: continue
				full = f"{db.name}/{pkg.name}"
				self.package_map[name] = full
				return [pkg]

		raise ValueError(f"package {name} not found")

	def lookup_package_depends(self, name: str, tree: list[str]):
		"""
		Lookup pyalpm package and all dependencies
		"""
		local: bool = False
		if ".pkg.tar." in name:
			pkg = self.handle.load_pkg(name)
			if not pkg:
				raise FileNotFoundError(f"package {name} not found")
			local = True
			pkgs = [pkg]
		else:
			if "/" in name and name in tree:
				return
			try:
				pkgs = self.lookup_package(name)
			except:
				log.warning(f"package {name} not found")
				return
		for pkg in pkgs:
			full = name if local else f"{pkg.db.name}/{pkg.name}"
			if full in tree: continue
			tree.append(full)
			for depend in pkg.depends:
				self.lookup_package_depends(depend, tree)

	def init_cache(self):
		"""
		Initialize pacman cache folder
		"""
		host_cache = "/var/cache/pacman/pkg" # host cache
		work_cache = os.path.join(self.ctx.work, "packages") # workspace cache
		root_cache = os.path.join(self.root, "var/cache/pacman/pkg") # rootfs cache
		self.caches.clear()

		# host cache is existing, use host cache folder
		if os.path.exists(host_cache):
			self.caches.append(host_cache)

		self.caches.append(work_cache)
		self.caches.append(root_cache)
		os.makedirs(work_cache, mode=0o0755, exist_ok=True)
		os.makedirs(root_cache, mode=0o0755, exist_ok=True)

	def add_repo(self, repo: PacmanRepo):
		if not repo or not repo.name or len(repo.servers) <= 0:
			raise ArchBuilderConfigError("bad repo")
		self.repos.append(repo)
		self.repos.sort(key=lambda r: r.priority)

	def init_repos(self):
		"""
		Initialize mirrors
		"""
		if "repo" not in self.config:
			raise ArchBuilderConfigError("no repos found in config")
		mirrors = self.ctx.get("mirrors", [])
		for repo in self.config["repo"]:
			if "name" not in repo:
				raise ArchBuilderConfigError("repo name not set")

			# never add local into database
			if repo["name"] == "local" or "/" in repo["name"]:
				raise ArchBuilderConfigError("bad repo name")

			# create pacman repo instance
			pacman_repo = PacmanRepo(self.ctx, name=repo["name"])
			if "priority" in repo:
				pacman_repo.priority = repo["priority"]

			if "mirrorlist" in repo:
				pacman_repo.mirrorlist = repo["mirrorlist"]

			# add public key url and id
			if "publickey" in repo and "keyid" not in repo:
				raise ArchBuilderConfigError("publickey is provided without keyid")

			if "publickey" in repo:
				pacman_repo.publickey = repo["publickey"]

			if "keyid" in repo:
				pacman_repo.keyid = repo["keyid"]

			servers: list[dict[str, str]] = []

			# add all repo url
			if "server" in repo: servers.append({"config_url": repo["server"]})
			if "servers" in repo: servers.extend({"config_url": url} for url in repo["server"])
			if len(servers) <= 0:
				raise ArchBuilderConfigError("no any original repo url found")

			# resolve repo url
			values = {
				"arch": self.ctx.tgt_arch,
				"repo": repo["name"],
			}
			for server in servers:
				server["real_url"] = resolve_simple_values(
					server["config_url"], values
				)

			# add repo mirror url
			for mirror in mirrors:
				if "name" not in mirror:
					raise ArchBuilderConfigError("mirror name not set")
				if "repos" not in mirror:
					raise ArchBuilderConfigError("repos list not set")
				for repo in mirror["repos"]:
					if "original" not in repo:
						raise ArchBuilderConfigError("original url not set")
					if "mirror" not in repo:
						raise ArchBuilderConfigError("mirror url not set")
					for server in servers:
						if server["config_url"].startswith(repo["original"]):
							len_orig = len(repo["original"])
							real_url = repo["mirror"] + server["real_url"][len_orig:]
							config_url = repo["mirror"] + server["config_url"][len_orig:]
							pacman_repo.add_server(
								name=mirror["name"],
								url=real_url,
								config_url=config_url,
								mirror=True,
							)

			# add url to repos
			for server in servers:
				pacman_repo.add_server(
					url=server["real_url"],
					config_url=server["config_url"],
					mirror=False
				)

			self.add_repo(pacman_repo)

	def __init__(self, ctx: ArchBuilderContext):
		"""
		Initialize pacman context
		"""
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
		self.package_map = {}
		self.caches = []
		self.repos = []
		self.pacman_key = PacmanKey(ctx)
		self.init_cache()
		self.init_repos()
		for cache in self.caches:
			self.handle.add_cachedir(cache)
		self.init_config()

	def uninstall(self, pkgs: list[str]):
		"""
		Uninstall packages via pacman
		"""
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
		"""
		Install packages via pacman
		"""
		if len(pkgs) == 0: return
		local_pkgs = [item for item in pkgs if ".pkg.tar." in item]
		dl_pkgs = [item for item in pkgs if ".pkg.tar." not in item]
		ps = " ".join(pkgs)
		log.info(f"installing packages {ps}")
		if dl_pkgs:
			self.download_all(dl_pkgs)
			args = ["--sync"]
			if not force: args.append("--needed")
			if asdeps: args.append("--asdeps")
			if nodeps: args.extend(["--nodeps", "--nodeps"])
			args.extend(dl_pkgs)
			self.pacman(args)
		if local_pkgs:
			self.install_local(local_pkgs)

	def download(self, pkgs: list[str], nogpg: bool=False):
		"""
		Download packages via pacman
		"""
		dl_pkgs = [item for item in pkgs if ".pkg.tar." not in item]
		if len(dl_pkgs) == 0: return
		core_db = "var/lib/pacman/sync/core.db"
		if not os.path.exists(os.path.join(self.root, core_db)):
			self.refresh()
		log.info("downloading packages %s", " ".join(dl_pkgs))
		args = ["--sync", "--downloadonly", "--nodeps", "--nodeps"]
		args.extend(dl_pkgs)
		tries = 0
		while True:
			try:
				self.pacman(args, nogpg=nogpg)
				break
			except:
				if tries < self.ctx.retry_count:
					log.warning("download packages failed, retry...", exc_info=True)
					tries += 1
					continue
				raise

	def download_all(self, pkgs: list[str]):
		"""
		Download packages and all dependencies
		"""
		pkg_once = 100
		packages: list[str] = []
		for pkg in pkgs:
			self.lookup_package_depends(pkg, packages)
		for once in range(0, len(packages), pkg_once):
			self.download(packages[once:once + pkg_once])

	def install_local(self, files: list[str]):
		"""
		Install a local packages via pacman
		"""
		if len(files) == 0: return
		log.info("installing local packages %s", " ".join(files))
		self.download_all(files)
		args = ["--needed", "--upgrade"]
		args.extend(files)
		self.pacman(args)

	def refresh(self, /, force: bool = False):
		"""
		Update local databases via pacman
		"""
		log.info("refresh pacman database")
		args = ["--sync", "--refresh"]
		if force: args.append("--refresh")
		self.pacman(args)

	def find_package_file(self, pkg: pyalpm.Package) -> str | None:
		"""
		Find out pacman package archive file in cache
		"""
		for cache in self.caches:
			p = os.path.join(cache, pkg.filename)
			if os.path.exists(p): return p
		return None

	def trust_keyring_pkg(self, pkg: pyalpm.Package):
		"""
		Trust a keyring package from file without install it
		"""
		if not self.ctx.gpgcheck: return
		names: list[str] = []
		target = os.path.join(self.ctx.work, "keyrings")
		keyring = "usr/share/pacman/keyrings/"

		# find out file path
		path = self.find_package_file(pkg)

		# cleanup keyring extract folder
		if os.path.exists(target):
			shutil.rmtree(target)
		os.makedirs(target, mode=0o0755)
		if path is None: raise RuntimeError(
			f"package {pkg.name} not found"
		)

		# open keyring package to extract
		log.debug(f"processing keyring package {pkg.name}")
		with libarchive.file_reader(path) as archive:
			for file in archive:
				pn: str = file.pathname
				if not pn.startswith(keyring): continue

				# get the filename of file
				fn = pn[len(keyring):]
				if len(fn) <= 0: continue

				# add keyring name to populate
				if fn.endswith(".gpg"): names.append(fn[:-4])

				# extract file
				dest = os.path.join(target, fn)
				log.debug(f"extracting {pn} to {dest}")
				with open(dest, "wb") as f:
					for block in file.get_blocks(file.size):
						f.write(block)
					fd = f.fileno()
					os.fchmod(fd, file.mode)
					os.fchown(fd, file.uid, file.gid)

		# trust extracted keyring
		self.pacman_key.pouplate_keys(names, target)

	def add_trust_keyring_pkg(self, pkgnames: list[str], nogpg: bool=False):
		"""
		Trust a keyring package from file without install it
		"""
		if not self.ctx.gpgcheck: return
		if len(pkgnames) <= 0: return
		self.download(pkgnames, nogpg=nogpg)
		for pkgname in pkgnames:
			pkgs = self.lookup_package(pkgname)
			for pkg in pkgs:
				self.trust_keyring_pkg(pkg)
