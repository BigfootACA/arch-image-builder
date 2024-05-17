from logging import getLogger
from builder.lib.serializable import SerializableDict
from builder.lib.area import Area
log = getLogger(__name__)


class DiskPart(SerializableDict):
	layout = None
	idx: int

	@property
	def part_name(self) -> str: pass

	@part_name.setter
	def part_name(self, name: str): pass

	@property
	def type(self) -> str: pass

	@type.setter
	def type(self, val: str): pass

	@property
	def id(self) -> str: pass

	@id.setter
	def id(self, val: str): pass

	@property
	def start_lba(self) -> int: pass

	@start_lba.setter
	def start_lba(self, start_lba: int): pass

	@property
	def end_lba(self) -> int: pass

	@end_lba.setter
	def end_lba(self, end_lba: int): pass

	@property
	def size_lba(self) -> int: pass

	@size_lba.setter
	def size_lba(self, size_lba: int): pass

	@property
	def partlabel(self) -> str: pass

	@property
	def partuuid(self) -> str: pass

	def to_area(self) -> Area:
		return Area(
			self.start_lba,
			self.end_lba,
			self.size_lba
		)

	def set_area(self, start: int = -1, end: int = -1, size: int = -1, area: Area = None):
		val = Area(start, end, size, area).fixup().to_tuple()
		self.start_lba, self.end_lba, self.size_lba = val

	def delete(self):
		self.layout.del_partition(self)

	@property
	def attributes(self) -> int: pass

	@attributes.setter
	def attributes(self, attributes: int): pass

	@property
	def start(self) -> int:
		return self.start_lba * self.layout.sector

	@start.setter
	def start(self, start: int):
		self.start_lba = start / self.layout.sector

	@property
	def end(self) -> int:
		return self.end_lba * self.layout.sector

	@end.setter
	def end(self, end: int):
		self.end_lba = end / self.layout.sector

	@property
	def size(self) -> int:
		return self.size_lba * self.layout.sector

	@size.setter
	def size(self, size: int):
		self.size_lba = size / self.layout.sector
