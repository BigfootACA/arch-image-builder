import os
import re
import pathlib
from packaging import version
from logging import getLogger
from builder.lib.context import ArchBuilderContext
log = getLogger(__name__)


class PacmanKey:
	def __init__(self, ctx: ArchBuilderContext):
		self.ctx= ctx
		self.gpgdir = os.path.join(ctx.get_rootfs(), "etc/pacman.d/gnupg")

	def gpg_cmd(self) -> list[str]:
		return [
			"gpg",
			"--homedir", self.gpgdir,
			"--no-permission-warning",
		]

	def gpg(self, args: list[str], stdin: str=None):
		"""
		Call gpg
		"""
		if not self.ctx.gpgcheck:
			raise RuntimeError("GPG check disabled")
		cmds = []
		cmds.extend(self.gpg_cmd())
		cmds.extend(args)
		ret = self.ctx.run_external(cmds, stdin=stdin)
		if ret != 0: raise OSError(f"gpg failed with {ret}")

	def gpg_eval(self, args: list[str], stdin: str=None) -> str:
		"""
		Call gpg and get stdout
		"""
		if not self.ctx.gpgcheck:
			raise RuntimeError("GPG check disabled")
		cmds = []
		cmds.extend(self.gpg_cmd())
		cmds.extend(args)
		ret, stdout = self.ctx.run_external(cmds, stdin=stdin, want_stdout=True)
		if ret != 0: raise OSError(f"gpg failed with {ret}")
		return stdout

	def gpg_version(self) -> version.Version:
		stdout = self.gpg_eval(["--version"])
		ver = stdout.split("\n")[0].split(" ")[2]
		log.debug(f"gpg version {ver}")
		return version.parse(ver)

	def initialize(self):
		log.debug("initialize pacman gpg folder...")
		if not os.path.isdir(self.gpgdir):
			os.makedirs(self.gpgdir, mode=0o755, exist_ok=True)
		gpg_conf = pathlib.Path(os.path.join(self.gpgdir, "gpg.conf"))
		agent_conf = pathlib.Path(os.path.join(self.gpgdir, "gpg-agent.conf"))
		pubring = pathlib.Path(os.path.join(self.gpgdir, "pubring.gpg"))
		secring = pathlib.Path(os.path.join(self.gpgdir, "secring.gpg"))
		trustdb = pathlib.Path(os.path.join(self.gpgdir, "trustdb.gpg"))
		if not pubring.exists(): pubring.touch(mode=0o644)
		if not secring.exists(): secring.touch(mode=0o600)
		if not trustdb.exists(): self.gpg(["--update-trustdb"])
		pubring.chmod(0o644)
		trustdb.chmod(0o644)
		secring.chmod(0o600)
		if not gpg_conf.exists():
			log.debug(f"create gpg config {gpg_conf}")
			with open(gpg_conf, "w+") as f:
				f.write("no-greeting\n")
				f.write("no-permission-warning\n")
				f.write("keyserver-options timeout=10\n")
				f.write("keyserver-options import-clean\n")
				if self.gpg_version() > version.parse("2.2.17"):
					f.write("keyserver-options no-self-sigs-only\n")
			gpg_conf.chmod(0o644)
		if not agent_conf.exists():
			log.debug(f"create gpg config {agent_conf}")
			with open(agent_conf, "w+") as f:
				f.write("disable-scdaemon")
			agent_conf.chmod(0o644)
		keys = self.gpg_eval(["-K", "--with-colons"])
		if not keys or len(keys.split("\n")) < 1:
			self.generate_master_key()

	def generate_master_key(self):
		log.info("Generating pacman master key. This may take some time.")
		self.gpg(["--gen-key", "--batch"], stdin=
			"%echo Generating pacman keyring master key...\n"
			"Key-Type: RSA\n"
			"Key-Length: 4096\n"
			"Key-Usage: sign\n"
			"Name-Real: Pacman Keyring Master Key\n"
			"Name-Email: pacman@localhost\n"
			"Expire-Date: 0\n"
			"%no-protection\n"
			"%commit\n"
			"%echo Done\n"
		)
		self.update_db()

	def update_db(self):
		log.debug(f"updating database...")
		self.gpg(["--batch", "--check-trustdb"])

	def add_keys_from(self, paths: list[str] | str, update: bool=True):
		items: list[str] = []
		if type(paths) is str:
			items.append(paths)
		elif type(paths) is list:
			items.extend(paths)
		else:
			raise TypeError("bad path type")
		for path in items:
			if path.startswith("-"):
				raise RuntimeError("bad path")
		if len(items) < 1:
			raise RuntimeError("no any path")
		log.debug(f"add keys from {items}")
		args = ["--quiet", "--batch", "--import"]
		args.extend(items)
		self.gpg(args)
		if update: self.update_db()

	def add_keys_with(self, content: str, update: bool=True):
		self.gpg(["--quiet", "--batch", "--import", "-"], stdin=content)
		if update: self.update_db()

	def key_lookup_from_name(self, name: str) -> str:
		result: str = None
		stdout = self.gpg_eval(["--search-keys", "--batch", "--with-colons", name])
		for line in stdout.split("\n"):
			cols = line.split(":")
			if cols[0] != "pub": continue
			if result is not None:
				raise RuntimeError(f"Key name is ambiguous: {name}")
			result = cols[1]
		if result is None:
			raise RuntimeError(f"Failed to lookup key by name: {name}")
		return result

	def recv_keys(self, keys: str | list[str], update: bool=True):
		"""
		Receive keys
		"""
		items = []
		if type(keys) is str:
			items.append(keys)
		elif type(keys) is list:
			if len(keys) <= 0: return
			items.extend(keys)
		else:
			raise TypeError("bad keys type")
		re_keyid = re.compile(r'(0x)?[0-9a-fA-F]+$')
		re_email = re.compile(r'[^\s@]+@[^\s@]+\.[^\s@]+$')
		emails = []
		keyids = []
		for item in items:
			if re_keyid.match(item):
				keyids.append(item)
			elif re_email.match(item):
				emails.append(item)
			else:
				keyids.append(self.key_lookup_from_name(item))
		if len(emails) > 0:
			log.debug(f"receive key by email {emails}")
			args = ["--auto-key-locate", "clear,nodefault,wkd,keyserver", "--locate-key"]
			args.extend(emails)
			self.gpg(args)
		if len(keyids) > 0:
			log.debug(f"receive key by key id {keyids}")
			args = ["--recv-keys"]
			args.extend(keyids)
			self.gpg(args)
		if update: self.update_db()

	def lsign_key(self, keys: str | list[str], update: bool=True):
		"""
		Local sign keys
		"""
		items = []
		if type(keys) is str:
			items.append(keys)
		elif type(keys) is list:
			if len(keys) <= 0: return
			items.extend(keys)
		else:
			raise TypeError("bad keys type")
		for key in items:
			log.debug(f"local sign key {key}")
			args = ["--command-fd", "0", "--quiet", "--batch", "--lsign-key", key]
			self.gpg(args, stdin="y\ny\n")
		if update: self.update_db()

	def pouplate_keys(
		self,
		names: str | list[str] = None,
		folder: str = None,
		update: bool=True
	):
		"""
		Populate all keys via pacman-key
		"""
		items = []
		if not folder:
			folder = os.path.join(self.ctx.get_rootfs(), "usr/share/pacman/keyrings")
		if names is None: pass
		elif type(names) is str:
			items.append(names)
		elif type(names) is list:
			items.extend(names)
		else:
			raise TypeError("bad names type")
		if len(items) == 0:
			for key in os.listdir(folder):
				if key.endswith(".gpg"):
					items.append(key[:-4])
		for key in items:
			path = os.path.join(folder, f"{key}.gpg")
			if not os.path.exists(path):
				raise FileNotFoundError(f"keyring {key} not found")
		if len(items) == 0:
			return
		for key in items:
			file = f"{key}.gpg"
			path = os.path.join(folder, file)
			log.info(f"Appending keys from {file}...")
			self.gpg(["--quiet", "--import", path])
		for key in items:
			file = f"{key}-trusted"
			path = os.path.join(folder, file)
			if not os.path.exists(path):
				continue
			log.debug(f"populate trust {key}")
			self.trust_key_from(path, update=False)
		for key in items:
			file = f"{key}-revoked"
			path = os.path.join(folder, file)
			if not os.path.exists(path):
				continue
			log.debug(f"populate revoke {key}")
			self.revoke_key_from(path, fail=True, update=False)
		if update: self.update_db()

	def trust_key_from(self, path: str, update: bool=True):
		with open(path, "r") as f:
			while True:
				line = f.readline()
				if not line:
					break
				line = line.strip()
				if len(line) <= 0 or line.startswith("#"):
					continue
				cols = line.split(":")
				if len(cols) > 1:
					self.lsign_key(cols[0], update=False)
		log.debug(f"import owner trust from {path}")
		self.gpg(["--import-ownertrust", path])
		if update: self.update_db()

	def revoke_key_from(self, path: str, fail: bool=False, update: bool=True):
		with open(path, "r") as f:
			while True:
				line = f.readline()
				if not line:
					break
				line = line.strip()
				if len(line) <= 0 or line.startswith("#"):
					continue
				try:
					self.revoke_key(line, update=False)
				except:
					if not fail: raise
					log.warning(f"revoke key {line} failed")
		if update: self.update_db()

	def revoke_key(self, keyid: str, update: bool=True):
		log.debug(f"revoke key {keyid}")
		args = [
			"--command-fd", "0",
			"--no-auto-check-trustdb",
			"--quiet", "--batch",
			"--edit-key", keyid,
		]
		self.gpg(args, stdin="disable\nquit\n")
		if update: self.update_db()
