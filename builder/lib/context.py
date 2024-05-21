import os
from copy import deepcopy
from datetime import datetime
from subprocess import Popen, PIPE
from logging import getLogger
from builder.lib.cpu import cpu_arch_get
from builder.lib.utils import parse_cmd_args
from builder.lib.subscript import dict_get
from builder.lib.loop import loop_detach
from builder.lib.mount import MountTab
from builder.lib.cgroup import CGroup
from builder.lib.subscript import SubScript
from builder.lib.shadow import PasswdFile, GroupFile
log = getLogger(__name__)


class ArchBuilderContext:

	"""
	Config from configs/{CONFIG}.yaml
	"""
	config: dict = {}
	config_orig: dict = {}

	"""
	Target name
	"""
	target: str = None
	tgt_arch: str = None

	"""
	CPU architecture
	"""
	cur_arch: str = cpu_arch_get()

	"""
	RootFS ready for chroot
	"""
	chroot: bool = False

	"""
	Repack rootfs only
	"""
	repack: bool = False

	"""
	Top tree folder
	"""
	dir: str = None

	"""
	Workspace folder
	"""
	work: str = None

	"""
	Current mounted list
	"""
	mounted: MountTab = MountTab()

	"""
	fstab for rootfs
	"""
	fstab: MountTab = MountTab()

	"""
	Enable GPG check for pacman packages and databases
	"""
	gpgcheck: bool = True

	"""
	Control group for chroot
	"""
	cgroup: CGroup = None

	"""
	File system map for host
	"""
	fsmap: dict = {}

	"""
	Loopback block for build
	"""
	loops: list[str] = []

	"""
	User config for rootfs
	"""
	passwd: PasswdFile = PasswdFile()
	group: GroupFile = GroupFile()

	"""
	Use a preset to build package
	"""
	preset: bool = False

	"""
	Package version
	"""
	version: str = datetime.now().strftime('%Y%m%d%H%M%S')

	def get(self, key: str, default=None):
		"""
		Get config value
		"""
		try: return dict_get(key, self.config)
		except: return default

	def get_rootfs(self): return os.path.join(self.work, "rootfs")
	def get_output(self): return os.path.join(self.work, "output")
	def get_mount(self): return os.path.join(self.work, "mount")

	def __init__(self):
		self.cgroup = CGroup("arch-image-builder")
		self.config["version"] = self.version
		try: self.cgroup.create()
		except: log.warning("failed to create cgroup", exc_info=1)

	def __deinit__(self):
		self.cleanup()

	def cleanup(self):
		"""
		Cleanup build context
		"""
		from builder.build.mount import undo_mounts
		self.cgroup.kill_all()
		self.cgroup.destroy()
		undo_mounts(self)
		for loop in self.loops:
			log.debug(f"detaching loop {loop}")
			loop_detach(loop)

	def run_external(
		self,
		cmd: str | list[str],
		/,
		cwd: str = None,
		env: dict = None,
		stdin: str | bytes = None
	) -> int:
		"""
		Run external command
		run_external("mke2fs -t ext4 ext4.img")
		"""
		args = parse_cmd_args(cmd)
		argv = " ".join(args)
		log.debug(f"running external command {argv}")
		fstdin = None if stdin is None else PIPE
		proc = Popen(args, cwd=cwd, env=env, stdin=fstdin)
		self.cgroup.add_pid(proc.pid)
		if stdin:
			if type(stdin) is str: stdin = stdin.encode()
			proc.stdin.write(stdin)
			proc.stdin.close()
		ret = proc.wait()
		log.debug(f"command exit with {ret}")
		return ret

	def reload_passwd(self):
		"""
		Reload user database
		"""
		root = self.get_rootfs()
		pf = os.path.join(root, "etc/passwd")
		gf = os.path.join(root, "etc/group")
		self.passwd.unload()
		self.group.unload()
		if os.path.exists(pf): self.passwd.load_file(pf)
		if os.path.exists(gf): self.group.load_file(gf)

	def finish_config(self):
		"""
		Done load configs
		"""
		self.config_orig = deepcopy(self.config)

	def resolve_subscript(self):
		"""
		Run subscript replaces
		"""
		ss = SubScript()
		self.config = deepcopy(self.config_orig)
		ss.parse(self.config)
