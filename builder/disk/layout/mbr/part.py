from logging import getLogger
from typing import Self
from builder.disk.layout.layout import DiskLayout, DiskPart
from builder.disk.layout.mbr.struct import MbrPartEntry
from builder.disk.layout.mbr.types import DiskTypesMBR
log = getLogger(__name__)


class DiskPartMBR(DiskPart):
	layout: DiskLayout
	boot_indicator: int
	os_indicator: int
	idx: int
	logical: bool
	extend: Self
	_start_lba: int
	_size_lba: int

	def get_root_ebr(self) -> Self:
		ebr = self
		while ebr.logical:
			ebr = ebr.extend
		return ebr

	@property
	def bootable(self) -> bool:
		return self.boot_indicator == 0x80

	@bootable.setter
	def bootable(self, bootable: bool):
		self.boot_indicator = 0x80 if bootable else 0

	@property
	def id(self) -> str:
		return f"{self.layout.id}-{self.idx+1}"

	@id.setter
	def id(self, val: str):
		raise NotImplementedError("cannot change id of mbr part")

	@property
	def type_id(self) -> int:
		return self.os_indicator

	@type_id.setter
	def type_id(self, tid: int):
		self.type = tid

	@property
	def type(self) -> str:
		return DiskTypesMBR.lookup_one_name(self.os_indicator)

	@type.setter
	def type(self, tid: str):
		g = DiskTypesMBR.lookup_one_id(tid)
		if g is None: raise ValueError(f"bad type {tid}")
		self.os_indicator = g

	@property
	def start_lba(self) -> int: return self._start_lba

	@start_lba.setter
	def start_lba(self, start_lba: int): self._start_lba = start_lba

	@property
	def size_lba(self) -> int: return self._size_lba

	@size_lba.setter
	def size_lba(self, size_lba: int): self._size_lba = size_lba

	@property
	def end_lba(self) -> int:
		return self.size_lba + self.start_lba - 1

	@end_lba.setter
	def end_lba(self, end_lba: int):
		self.size_lba = end_lba - self.start_lba + 1

	def load_entry(self, part: MbrPartEntry):
		self.start_lba = part.start_lba
		self.size_lba = part.size_lba
		self.boot_indicator = part.boot_indicator
		self.os_indicator = part.os_indicator

	def to_entry(self) -> MbrPartEntry:
		part = MbrPartEntry()
		part.start_lba = self.start_lba
		part.size_lba = self.size_lba
		part.boot_indicator = self.boot_indicator
		part.os_indicator = self.os_indicator
		return part

	def __init__(self, layout: DiskLayout, part: MbrPartEntry, idx: int):
		super().__init__()
		self.layout = layout
		self.idx = idx
		self.start_lba = 0
		self.size_lba = 0
		self.boot_indicator = 0
		self.os_indicator = 0
		self.logical = False
		self.extend = None
		if part: self.load_entry(part)
		from builder.disk.layout.mbr.layout import DiskLayoutMBR
		if not isinstance(layout, DiskLayoutMBR):
			raise TypeError("require DiskLayoutGPT")

	def to_dict(self) -> dict:
		return {
			"logical": self.logical,
			"bootable": self.bootable,
			"type_id": self.type_id,
			"type_name": self.type,
			"start_lba": self.start_lba,
			"end_lba": self.end_lba,
			"size_lba": self.size_lba,
		}
