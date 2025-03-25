import os
import time
import signal
from builder.lib.mount import MountTab
from logging import getLogger
log = getLogger(__name__)


class CGroup:
	fs: str
	name: str

	@property
	def path(self) -> str:
		"""
		Get full path of this cgroup
		"""
		return os.path.join(self.fs, self.name)

	@property
	def valid(self) -> bool:
		"""
		Can read or write to this cgroup
		"""
		return os.path.exists(self.path)

	def create(self):
		"""
		Create this cgroup now
		"""
		if self.valid: return
		os.mkdir(self.path)

	def destroy(self):
		"""
		Destroy the cgroup
		"""
		if not self.valid: return
		os.rmdir(self.path)

	def add_pid(self, pid: int):
		"""
		Add a pid to track
		"""
		if not self.valid: return
		procs = os.path.join(self.path, "cgroup.procs")
		with open(procs, "w") as f:
			f.write(f"{pid}\n")

	def list_pid(self) -> list[int]:
		"""
		List all tracked children progress id
		"""
		ret: list[int] = []
		if not self.valid: return ret
		procs = os.path.join(self.path, "cgroup.procs")
		with open(procs, "r") as f:
			for line in f:
				ret.append(int(line))
		return ret

	def kill_all(self, sig: int = signal.SIGTERM, timeout: int = 10, kill: int = 8):
		"""
		Kill all children process and wait them exit
		"""
		if not self.valid: return
		pids = self.list_pid()
		remain = 0
		while True:
			# send a signal
			for pid in pids:
				log.debug(f"killing {pid}")
				try: os.kill(pid, sig)
				except: pass

			# waitpid to clean zombie
			try: os.waitpid(-1, os.WNOHANG)
			except: pass

			# check all children was exited
			pids = self.list_pid()
			if len(pids) <= 0: break

			# set to SIGKILL when reached kill time
			if 0 < kill <= remain:
				sig = signal.SIGKILL

			# timeoutd, throw out
			if remain >= timeout:
				raise TimeoutError("killing pids timedout")

			# wait...
			time.sleep(1)

	def find_pid_ctrl(self) -> str:
		tab = MountTab.parse_mounts()
		for cg in tab.find_target("/sys/fs/cgroup"):
			if cg.fstype == "cgroup2":
				return cg.target
		for cg in tab.find_fstype("cgroup"):
			if "pids" in cg.option:
				return cg.target
		for cg in tab.find_fstype("cgroup2"):
			return cg.target
		raise OSError("no pids cgroup found")

	def __init__(self, name: str, fs: str = None):
		self.fs = fs if fs else self.find_pid_ctrl()
		self.name = name
