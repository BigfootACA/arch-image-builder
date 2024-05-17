import os
import time
import signal
from logging import getLogger
log = getLogger(__name__)


class CGroup:
	fs: str = "/sys/fs/cgroup"
	name: str

	@property
	def path(self) -> str:
		return os.path.join(self.fs, self.name)

	@property
	def valid(self) -> bool:
		return os.path.exists(self.path)

	def create(self):
		if self.valid: return
		os.mkdir(self.path)

	def destroy(self):
		if not self.valid: return
		os.rmdir(self.path)

	def add_pid(self, pid: int):
		if not self.valid: return
		procs = os.path.join(self.path, "cgroup.procs")
		with open(procs, "w") as f:
			f.write(f"{pid}\n")

	def list_pid(self) -> list[int]:
		ret: list[int] = []
		if not self.valid: return ret
		procs = os.path.join(self.path, "cgroup.procs")
		with open(procs, "r") as f:
			for line in f:
				ret.append(int(line))
		return ret

	def kill_all(self, sig: int = signal.SIGTERM, timeout: int = 10, kill: int = 8):
		if not self.valid: return
		pids = self.list_pid()
		remain = 0
		while True:
			for pid in pids:
				log.debug(f"killing {pid}")
				try: os.kill(pid, sig)
				except: pass
			try: os.waitpid(-1, os.WNOHANG)
			except: pass
			pids = self.list_pid()
			if len(pids) <= 0: break
			if 0 < kill <= remain:
				sig = signal.SIGKILL
			if remain >= timeout:
				raise TimeoutError("killing pids timedout")
			time.sleep(1)

	def __init__(self, name: str, fs: str = None):
		if fs: self.fs = fs
		self.name = name
