import io
import os
import libmount
from typing import Self
from logging import getLogger
from builder.lib.blkid import Blkid
from builder.lib.serializable import SerializableDict,SerializableList
log = getLogger(__name__)

virtual_fs = [
	"sysfs", "tmpfs", "proc", "cgroup", "cgroup2", "hugetlbfs",
	"devtmpfs", "binfmt_misc", "configfs", "debugfs", "tracefs", "cpuset",
	"securityfs", "sockfs", "bpf", "pipefs", "ramfs", "binder", "bdev",
	"devpts", "autofs", "efivarfs", "mqueue", "resctrl", "pstore", "fusectl",
]

real_fs = [
	"reiserfs", "ext4", "ext3", "ext2", "cramfs", "squashfs", "minix", "vfat",
	"msdos", "exfat", "iso9660", "hfsplus", "gfs2meta", "ecryptfs", "ntfs3", "ufs",
	"jffs2", "ubifs", "affs", "romfs", "ocfs2_dlmfs", "omfs", "jfs", "xfs", "nilfs2",
	"befs", "ocfs2", "btrfs", "hfs", "gfs2", "udf", "f2fs", "bcachefs", "erofs",
]


class MountPoint(SerializableDict):
	device: str = None
	source: str = None
	target: str = None
	fstype: str = None
	option: list[str] = []
	fs_freq: int = 0
	fs_passno: int = 0

	@property
	def virtual(self) -> bool:
		if self.fstype:
			if self.fstype in virtual_fs: return True
			if self.fstype in real_fs: return False
		if self.device:
			if self.device.startswith(os.sep): return False
		if self.source:
			if self.source.startswith(os.sep): return False
			if "=" in self.source: return False
		return True

	@property
	def level(self) -> int:
		if self.target is None: return 0
		path = os.path.realpath(self.target)
		cnt = path.count(os.sep)
		if (
			path.startswith(os.sep) and
			not path.endswith(os.sep)
		): cnt += 1
		return cnt

	@property
	def options(self):
		return ",".join(self.option)

	@options.setter
	def options(self, val: str):
		self.option = val.split(",")

	def get_option(self, opt: str) -> str | None:
		if opt in self.option:
			return opt
		if "=" not in opt:
			start = f"{opt}="
			values = (o for o in self.option if o.startswith(start))
			return next(values, None)
		return None

	def remove_option(self, opt: str | list[str]) -> Self:
		if type(opt) is list[str]:
			for o in opt:
				self.remove_option(o)
			return
		if opt in self.option:
			self.option.remove(opt)
			return
		if "=" in opt: opt = opt[:opt.find("=")]
		val = self.get_option(opt)
		if val:
			self.remove_option(val)
		return self

	def exclusive_option(self, opt: str, opt1: str, opt2: str) -> Self:
		if opt == opt1 or opt == opt2:
			self.remove_option(opt1)
		return self

	def add_option(self, opt: str) -> Self:
		self.exclusive_option(opt, "ro", "rw")
		self.exclusive_option(opt, "dev", "nodev")
		self.exclusive_option(opt, "suid", "nosuid")
		self.exclusive_option(opt, "exec", "noexec")
		self.exclusive_option(opt, "relatime", "noatime")
		self.remove_option(opt)
		if opt not in self.option:
			self.option.append(opt)
		return self

	def ro(self) -> Self:
		self.add_option("ro")
		return self

	def rw(self) -> Self:
		self.add_option("rw")
		return self

	def have_source(self) -> bool: return self.source and self.source != "none"
	def have_target(self) -> bool: return self.target and self.target != "none"
	def have_fstype(self) -> bool: return self.fstype and self.fstype != "none"
	def have_options(self) -> bool: return len(self.option) > 0

	def update_device(self):
		if self.virtual or self.source is None: return
		if self.source.startswith(os.sep):
			self.device = self.source
			return
		if "=" in self.source:
			self.device = Blkid().evaluate_tag(self.source)
			return

	def persist_source(self, tag: str = "UUID"):
		if self.virtual: return
		if self.device is None: self.update_device()
		if self.device is None: return
		tag = tag.upper()
		if tag == "PATH":
			self.source = self.device
			return
		self.source = Blkid().get_tag_value(
			None, tag, self.device
		)

	def tolibmount(self) -> libmount.Context:
		mnt = libmount.Context()
		mnt.target = self.target
		if self.have_source(): mnt.source = self.source
		if self.have_fstype(): mnt.fstype = self.fstype
		if self.have_options(): mnt.options = self.options
		return mnt

	def ismount(self) -> bool:
		return os.path.ismount(self.target)

	def mount(self) -> Self:
		if not os.path.exists(self.target):
			os.makedirs(self.target, mode=0o0755)
		if not os.path.ismount(self.target):
			log.debug(
				f"try mount {self.source} "
				f"to {self.target} "
				f"as {self.fstype} "
				f"with {self.options}"
			)
			lib = self.tolibmount()
			lib.mount()
		return self

	def umount(self) -> Self:
		if os.path.ismount(self.target):
			lib = self.tolibmount()
			lib.umount()
			log.debug(f"umount {self.target} successfuly")
		return self

	def from_mount_line(self, line: str) -> Self:
		d = line.split()
		if len(d) != 6:
			raise ValueError("bad mount line")
		self.source = d[0]
		self.target = d[1]
		self.fstype = d[2]
		self.options = d[3]
		self.fs_freq = int(d[4])
		self.fs_passno = int(d[5])
		return self

	def to_mount_line(self) -> str:
		self.fixup()
		fields = [
			self.source,
			self.target,
			self.fstype,
			self.options,
			str(self.fs_freq),
			str(self.fs_passno),
		]
		return " ".join(fields)

	def fixup(self) -> Self:
		if not self.have_source(): self.source = "none"
		if not self.have_target(): self.target = "none"
		if not self.have_fstype(): self.fstype = "none"
		if not self.have_options(): self.options = "defaults"
		return self

	def clone(self) -> Self:
		mnt = MountPoint()
		mnt.device = self.device
		mnt.source = self.source
		mnt.target = self.target
		mnt.fstype = self.fstype
		mnt.option = self.option
		mnt.fs_freq = self.fs_freq
		mnt.fs_passno = self.fs_passno
		return mnt

	def __init__(
		self,
		data: dict = None,
		device: str = None,
		source: str = None,
		target: str = None,
		fstype: str = None,
		options: str = None,
		option: list[str] = None,
		fs_freq: int = None,
		fs_passno: int = None,
	):
		super().__init__()
		self.device = None
		self.source = None
		self.target = None
		self.fstype = None
		self.option = []
		self.fs_freq = 0
		self.fs_passno = 0
		if data: self.from_dict(data)
		if device: self.device = device
		if source: self.source = source
		if target: self.target = target
		if fstype: self.fstype = fstype
		if options: self.options = options
		if option: self.option = option
		if fs_freq: self.fs_freq = fs_freq
		if fs_passno: self.fs_passno = fs_passno

	@staticmethod
	def parse_mount_line(line: str):
		return MountPoint().from_mount_line(line)


class MountTab(list[MountPoint], SerializableList):
	def find_folder(self, folder: str) -> Self:
		root = os.path.realpath(folder)
		return [mnt for mnt in self if mnt.target.startswith(root)]

	def find_target(self, target: str) -> Self: return [mnt for mnt in self if mnt.target == target]
	def find_source(self, source: str) -> Self: return [mnt for mnt in self if mnt.source == source]
	def find_fstype(self, fstype: str) -> Self: return [mnt for mnt in self if mnt.fstype == fstype]

	def clone(self) -> Self:
		mnts = MountTab()
		for mnt in self:
			mnts.append(mnt.clone())
		return mnts

	def mount_all(self, prefix: str = None, mkdir: bool = False) -> Self:
		for mnt in self:
			m = mnt.clone()
			if prefix:
				if m.target == "/": m.target = prefix
				else: m.target = os.path.join(prefix, m.target[1:])
			if mkdir and not os.path.exists(m.target):
				os.makedirs(m.target, mode=0o0755)
			m.mount()
		return self

	def resort(self):
		self.sort(key=lambda x: (x.level, len(x.target), x.target))

	def strip_virtual(self) -> Self:
		for mnt in self:
			if mnt.virtual:
				self.remove(mnt)
		return self

	def to_list(self) -> list:
		return self

	def from_list(self, o: list) -> Self:
		self.clear()
		for i in o: self.append(MountPoint().from_dict(i))
		return self

	def to_mount_file(self, linesep=os.linesep) -> str:
		ret = "# Source Target FS-Type Options FS-Freq FS-Dump"
		ret += linesep
		for point in self:
			ret += point.to_mount_line()
			ret += linesep
		return ret

	def write_mount_file(self, fp: io.TextIOWrapper):
		fp.write(self.to_mount_file())
		fp.flush()

	def create_mount_file(self, path: str) -> Self:
		with open(path, "w") as f:
			self.write_mount_file(f)
		return self

	def load_mount_fp(self, fp: io.TextIOWrapper) -> Self:
		for line in fp:
			if line is None: break
			line = line.strip()
			if len(line) <= 0: continue
			if line.startswith("#"): continue
			mnt = MountPoint.parse_mount_line(line)
			self.append(mnt)
		return self

	def load_mount_file(self, file: str) -> Self:
		with open(file, "r") as f:
			self.load_mount_fp(f)
		return self

	def load_fstab(self) -> Self:
		self.load_mount_file("/etc/fstab")
		return self

	def load_mounts(self) -> Self:
		self.load_mount_file("/proc/mounts")
		return self

	def load_mounts_pid(self, pid: int) -> Self:
		path = f"/proc/{pid}/mounts"
		self.load_mount_file(path)
		return self

	def from_mount_fp(self, fp: io.TextIOWrapper) -> Self:
		self.clear()
		self.load_mount_fp(fp)
		return self

	def from_mount_file(self, file: str) -> Self:
		self.clear()
		self.load_mount_file(file)
		return self

	def from_fstab(self, ) -> Self:
		self.clear()
		self.load_fstab()
		return self

	def from_mounts(self, ) -> Self:
		self.clear()
		self.load_mounts()
		return self

	def from_mounts_pid(self, pid: int) -> Self:
		self.clear()
		self.load_mounts_pid(pid)
		return self

	@staticmethod
	def parse_mount_fp(fp: io.TextIOWrapper):
		return MountTab().from_mount_fp(fp)

	@staticmethod
	def parse_mount_file(file: str):
		return MountTab().from_mount_file(file)

	@staticmethod
	def parse_fstab():
		return MountTab().from_fstab()

	@staticmethod
	def parse_mounts():
		return MountTab().from_mounts()

	@staticmethod
	def parse_mounts_pid(pid: int):
		return MountTab().from_mounts_pid(pid)
