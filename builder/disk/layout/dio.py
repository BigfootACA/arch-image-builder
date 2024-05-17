import os
import io
import stat
import fcntl
import ctypes
from logging import getLogger
from builder.disk.layout import ioctl
from builder.lib.utils import bytes_pad
log = getLogger(__name__)


class DiskIO:
	_min_sector: int
	_fp: io.RawIOBase
	_opened: bool
	_sector: int
	_cached: dict
	align: int

	def load_block_info(self):
		if self._fp is None: return
		fd = self._fp.fileno()
		st = os.fstat(fd)
		if not stat.S_ISBLK(st.st_mode): return
		try:
			val = ctypes.c_uint()
			fcntl.ioctl(fd, ioctl.BLKSSZGET, val)
			log.debug(f"Block sector size: {val.value}")
			self._sector = val.value
		except: pass
		try:
			val = ctypes.c_uint64()
			fcntl.ioctl(fd, ioctl.BLKGETSIZE64, val)
			log.debug(f"Block total size: {val.value}")
			self._cached["total_size"] = val.value
			self._cached["total_lba"] = val.value // self._sector
		except: pass
		try:
			val = ioctl.HDGeometry()
			fcntl.ioctl(fd, ioctl.HDIO_GETGEO, val)
			log.debug(f"Block heads: {val.heads.value}")
			log.debug(f"Block sectors: {val.sectors.value}")
			log.debug(f"Block cylinders: {val.cylinders.value}")
			log.debug(f"Block start: {val.start.value}")
			self._cached["heads"] = val.heads.value
			self._cached["sectors"] = val.sectors.value
			self._cached["cylinders"] = val.cylinders.value
			self._cached["start"] = val.start.value
		except: pass

	@property
	def sector(self) -> int:
		return self._sector

	@property
	def align_lba(self) -> int:
		return self.align // self.sector

	@align_lba.setter
	def align_lba(self, v: int):
		self.align = v * self.sector

	@property
	def total_size(self) -> int:
		if "total_size" in self._cached:
			return self._cached["total_size"]
		off = self._fp.tell()
		try:
			self._fp.seek(0, os.SEEK_END)
			ret = int(self._fp.tell())
		finally:
			self._fp.seek(off, os.SEEK_SET)
		return ret

	@property
	def total_lba(self) -> int:
		if "total_lba" in self._cached:
			return self._cached["total_lba"]
		size = self.total_size
		if size % self.sector != 0:
			raise ValueError("size misaligned with sector size")
		return size // self.sector

	def seek_lba(self, lba: int) -> int:
		if lba >= self.total_lba:
			raise ValueError("lba out of file")
		return self._fp.seek(self.sector * lba, os.SEEK_SET)

	def read_lba(self, lba: int) -> bytes:
		off = self._fp.tell()
		try:
			self.seek_lba(lba)
			ret = self._fp.read(self.sector)
		finally:
			self._fp.seek(off, os.SEEK_SET)
		return ret

	def read_lbas(self, lba: int, count: int = 0) -> bytes:
		return bytes().join(self.read_lba(lba + i) for i in range(count))

	def write_lba(self, lba: int, b: bytes) -> int:
		if not self._fp.writable():
			raise IOError("write is not allow")
		off = self._fp.tell()
		try:
			data = bytes_pad(b, self.sector, trunc=True)
			self.seek_lba(lba)
			ret = self._fp.write(data)
		finally:
			self._fp.seek(off, os.SEEK_SET)
		return ret

	def write_lbas(self, lba: int, b: bytes, count: int = 0) -> bytes:
		s = self.sector
		if count == 0:
			if len(b) % s != 0: raise ValueError(
				"buffer misaligned with sector size"
			)
			count = len(b) // s
		if count * s > len(b):
			raise ValueError("buffer too small")
		for i in range(count):
			t = b[i * s:(i + 1) * s]
			self.write_lba(lba + i, t)
		return b

	def __init__(self):
		self._min_sector = 512
		self._fp = None
		self._opened = False
		self._sector = 0
		self._cached = {}
		self.align = 0x100000
