import ctypes
from logging import getLogger
from builder.lib.serializable import SerializableDict
from builder.disk.layout.mbr.types import DiskTypesMBR
log = getLogger(__name__)


class MbrPartEntry(ctypes.Structure, SerializableDict):
	_fields_ = [
		("boot_indicator",  ctypes.c_uint8),
		("start_head",      ctypes.c_uint8),
		("start_sector",    ctypes.c_uint8),
		("start_track",     ctypes.c_uint8),
		("os_indicator",    ctypes.c_uint8),
		("end_head",        ctypes.c_uint8),
		("end_sector",      ctypes.c_uint8),
		("end_track",       ctypes.c_uint8),
		("start_lba",       ctypes.c_uint32),
		("size_lba",        ctypes.c_uint32),
	]
	heads: int=255
	sectors: int=63

	def is_bootable(self) -> bool:
		return self.boot_indicator == 0x80

	def set_bootable(self, bootable: bool):
		self.boot_indicator = 0x80 if bootable else 0

	def get_type_name(self) -> str:
		return DiskTypesMBR.lookup_one_name(self.os_indicator)

	def get_type_id(self) -> int:
		return DiskTypesMBR.lookup_one_id(self.os_indicator)

	def set_type(self, t: int|str):
		g = DiskTypesMBR.lookup_one_id(t)
		if g is None: raise ValueError(f"bad type {t}")
		self.os_indicator = g

	def set_start_lba(self, start_lba: int):
		c, h, s = lba_to_chs(start_lba, self.sectors, self.heads)
		self.start_head = h
		self.start_sector = s
		self.start_track = c
		self.start_lba = start_lba

	def set_end_lba(self, end_lba: int):
		c, h, s = lba_to_chs(end_lba, self.sectors, self.heads)
		self.end_head = h
		self.end_sector = s
		self.end_track = c
		self.size_lba = end_lba - self.start_lba + 1

	def set_size_lba(self, size_lba: int):
		end_lba = size_lba + self.start_lba - 1
		c, h, s = lba_to_chs(end_lba, self.sectors, self.heads)
		self.end_head = h
		self.end_sector = s
		self.end_track = c
		self.size_lba = size_lba

	def to_dict(self) -> dict:
		ret = {field[0]: getattr(self, field[0]) for field in self._fields_}
		ret["bootable"] = self.is_bootable()
		ret["type_id"] = self.get_type_id()
		ret["type_name"] = self.get_type_name()
		return ret


class MasterBootRecord(ctypes.Structure, SerializableDict):
	_pack_ = 1
	_fields_ = [
		("boot_code",   ctypes.c_byte * 440),
		("mbr_id",      ctypes.c_uint32),
		("reserved",    ctypes.c_uint16),
		("partitions",  MbrPartEntry * 4),
		("signature",   ctypes.c_uint16),
	]
	MBR_SIGNATURE: int = 0xaa55

	def fill_header(self):
		self.signature = self.MBR_SIGNATURE

	def check_signature(self) -> bool:
		return self.signature == self.MBR_SIGNATURE

	def to_dict(self) -> dict:
		parts = [part for part in self.partitions if part.os_indicator != 0]
		return {
			"mbr_id": f"{self.mbr_id:08x}",
			"partitions": parts,
			"signature": self.signature,
		}


assert(ctypes.sizeof(MbrPartEntry()) == 16)
assert(ctypes.sizeof(MasterBootRecord()) == 512)


def lba_to_chs(lba: int, sectors: int = 63, heads: int = 255):
	lba += 1
	sector = lba % sectors
	head = (lba // sectors) % heads
	cylinder = lba // (sectors * heads)
	return cylinder, head, sector
