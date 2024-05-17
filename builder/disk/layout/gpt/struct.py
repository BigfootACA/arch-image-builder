import ctypes
from uuid import UUID
from logging import getLogger
from builder.lib.utils import bytes_pad
from builder.lib.serializable import SerializableDict
from builder.disk.layout.gpt.types import DiskTypesGPT
from builder.disk.layout.gpt.uefi import EfiTableHeader, EfiGUID
log = getLogger(__name__)


class EfiPartTableHeader(ctypes.Structure, SerializableDict):
	_pack_ = 1
	_fields_ = [
		("header",           EfiTableHeader),
		("current_lba",      ctypes.c_uint64),
		("alternate_lba",    ctypes.c_uint64),
		("first_usable_lba", ctypes.c_uint64),
		("last_usable_lba",  ctypes.c_uint64),
		("disk_guid",        EfiGUID),
		("part_entry_lba",   ctypes.c_uint64),
		("entries_count",    ctypes.c_uint32),
		("entry_size",       ctypes.c_uint32),
		("entries_crc32",    ctypes.c_uint32),
	]
	EFI_PART_SIGN = b'EFI PART'

	@property
	def signature(self) -> ctypes.c_uint64:
		return self.header.signature

	@property
	def revision(self) -> ctypes.c_uint64:
		return self.header.revision

	@property
	def header_size(self) -> ctypes.c_uint64:
		return self.header.header_size

	@property
	def crc32(self) -> ctypes.c_uint64:
		return self.header.crc32

	def fill_header(self):
		self.header.set_signature(self.EFI_PART_SIGN)
		self.header.header_size = 92
		self.header.revision = 0x00010000

	def check_header(self) -> bool:
		if not self.header.check_signature(self.EFI_PART_SIGN):
			log.debug("GPT signature mismatch")
			return False
		if self.header.header_size < 92:
			log.debug("GPT header size too small")
			log.debug(f"{self.header.header_size} < 92")
			return False
		if not self.header.check_revision(1, 0):
			log.debug("GPT revision mismatch")
			log.debug(f"{self.header.get_revision()} != 1.0")
			return False
		if not self.header.check_crc32():
			log.debug("GPT crc32 check failed")
			return False
		if self.entry_size != 128:
			log.debug("GPT entry size unsupported")
			log.debug(f"{self.entry_size} != 128")
			return False
		return True

	def to_dict(self) -> dict:
		return {
			"header": self.header,
			"current_lba": self.current_lba,
			"alternate_lba": self.alternate_lba,
			"first_usable_lba": self.first_usable_lba,
			"last_usable_lba": self.last_usable_lba,
			"disk_guid": str(self.disk_guid),
			"part_entry_lba": self.part_entry_lba,
			"entries_count": self.entries_count,
			"entry_size": self.entry_size,
			"entries_crc32": self.entries_crc32,
		}


class EfiPartEntry(ctypes.Structure, SerializableDict):
	_pack_ = 1
	_fields_ = [
		("type_guid",       EfiGUID),
		("unique_guid",     EfiGUID),
		("start_lba",       ctypes.c_uint64),
		("end_lba",         ctypes.c_uint64),
		("attributes",      ctypes.c_uint64),
		("part_name",       ctypes.c_byte * 72),
	]

	def get_type_name(self) -> str:
		return DiskTypesGPT.lookup_one_name(self.type_guid)

	def get_type_uuid(self) -> UUID:
		return DiskTypesGPT.lookup_one_uuid(self.type_guid)

	def set_type(self, t: EfiGUID | UUID | str):
		g = DiskTypesGPT.lookup_one_guid(t)
		if g is None: raise ValueError(f"bad type {t}")
		self.type_guid = g

	def get_part_name(self) -> str:
		return self.part_name.decode("UTF-16LE").rstrip('\u0000')

	def set_part_name(self, name: str):
		size = EfiPartEntry.part_name.size
		data = name.encode("UTF-16LE")
		if len(data) >= size: raise ValueError("name too long")
		data = bytes_pad(data, size)
		ctypes.memmove(self.part_name, data, size)

	def check_type(self, t: EfiGUID | UUID | str) -> bool:
		return DiskTypesGPT.equal(self.type_guid, t)

	@property
	def total_lba(self):
		return self.end_lba - self.start_lba + 1

	def to_dict(self) -> dict:
		return {
			"type_guid": str(self.type_guid),
			"unique_guid": str(self.unique_guid),
			"start_lba": self.start_lba,
			"end_lba": self.end_lba,
			"attributes": self.attributes,
			"part_name": self.get_part_name(),
		}


assert(ctypes.sizeof(EfiPartTableHeader()) == 92)
assert(ctypes.sizeof(EfiPartEntry()) == 128)
