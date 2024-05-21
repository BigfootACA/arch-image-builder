from uuid import UUID
from logging import getLogger
from builder.disk.layout.layout import DiskLayout, DiskPart
from builder.disk.layout.gpt.struct import EfiPartEntry
from builder.disk.layout.mbr.struct import MbrPartEntry
from builder.disk.layout.gpt.types import DiskTypesGPT
from builder.disk.layout.mbr.types import DiskTypesMBR
from builder.disk.layout.gpt.uefi import EfiGUID
log = getLogger(__name__)


class DiskPartGPT(DiskPart):
	layout: DiskLayout
	mbr_type: int
	type_uuid: UUID
	bootable: bool
	uuid: UUID
	hybrid: bool
	idx: int
	_part_name: str
	_attributes: int
	_start_lba: int
	_end_lba: int

	@property
	def part_name(self) -> str: return self._part_name

	@part_name.setter
	def part_name(self, name: str): self._part_name = name

	@property
	def id(self) -> str:
		return str(self.uuid)

	@id.setter
	def id(self, val: str):
		self.uuid = UUID(val)

	@property
	def type(self) -> str:
		return DiskTypesGPT.lookup_one_name(self.type_uuid)

	@type.setter
	def type(self, val: str):
		tid = DiskTypesGPT.lookup_one_uuid(val)
		if tid is None: raise ValueError(f"unknown type {val}")
		self.type_uuid = tid
		if self.hybrid:
			tid = DiskTypesMBR.lookup_one_id(val)
			if tid is None: raise ValueError(f"unknown type {val}")
			self.mbr_type = tid

	@property
	def start_lba(self) -> int:
		return self._start_lba

	@start_lba.setter
	def start_lba(self, start_lba: int):
		self._start_lba = start_lba

	@property
	def end_lba(self) -> int:
		return self._end_lba

	@end_lba.setter
	def end_lba(self, end_lba: int):
		self._end_lba = end_lba

	@property
	def size_lba(self) -> int:
		return self.end_lba - self.start_lba + 1

	@size_lba.setter
	def size_lba(self, size_lba: int):
		self.end_lba = size_lba + self.start_lba - 1

	@property
	def attributes(self) -> int:
		return self._attributes

	@attributes.setter
	def attributes(self, attributes: int):
		self._attributes = attributes

	@property
	def partlabel(self) -> str:
		return self.part_name

	@property
	def partuuid(self) -> str:
		return self.id

	def load_entry(self, part: EfiPartEntry):
		self.type_uuid = part.type_guid.to_uuid()
		self.uuid = part.unique_guid.to_uuid()
		self.start_lba = part.start_lba
		self.end_lba = part.end_lba
		self.attributes = part.attributes
		self.part_name = part.get_part_name()

	def to_entry(self) -> EfiPartEntry:
		part = EfiPartEntry()
		part.type_guid = EfiGUID.from_uuid(self.type_uuid)
		part.unique_guid = EfiGUID.from_uuid(self.uuid)
		part.start_lba = self.start_lba
		part.end_lba = self.end_lba
		part.attributes = self.attributes
		part.set_part_name(self.part_name)
		return part

	def to_mbr_entry(self) -> MbrPartEntry:
		part = MbrPartEntry()
		part.set_bootable(self.bootable)
		part.set_type(self.mbr_type)
		part.set_start_lba(self.start_lba)
		part.set_size_lba(self.size_lba)
		return part

	def __init__(
		self,
		layout: DiskLayout,
		part: EfiPartEntry | None,
		idx: int
	):
		super().__init__()
		self.layout = layout
		self.idx = idx
		self.hybrid = False
		self.bootable = False
		self.part_name = None
		self.mbr_type = 0
		self.start_lba = 0
		self.end_lba = 0
		self.attributes = 0
		if part: self.load_entry(part)
		from builder.disk.layout.gpt.layout import DiskLayoutGPT
		if not isinstance(layout, DiskLayoutGPT):
			raise TypeError("require DiskLayoutGPT")

	def to_dict(self) -> dict:
		return {
			"type_uuid": self.type_uuid,
			"type_name": self.type,
			"uuid": self.uuid,
			"part_name": self.part_name,
			"attributes": self.attributes,
			"start_lba": self.start_lba,
			"end_lba": self.end_lba,
			"size_lba": self.size_lba,
		}
