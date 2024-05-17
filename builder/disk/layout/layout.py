from math import ceil
from io import RawIOBase
from logging import getLogger
from builder.lib.utils import size_to_bytes
from builder.lib.serializable import SerializableDict
from builder.lib.area import Area
from builder.disk.layout.dio import DiskIO
from builder.disk.layout.area import DiskArea
from builder.disk.layout.part import DiskPart
log = getLogger(__name__)


class DiskLayout(DiskIO, DiskArea, SerializableDict):
	partitions: list[DiskPart]
	loaded: bool

	@property
	def id(self) -> str: pass

	@id.setter
	def id(self, val: str): pass

	def create(self): pass

	def reload(self): pass

	def unload(self): pass

	def save(self): pass

	def set_from(self, config: dict): pass

	def size_to_bytes(self, value: str | int, alt_units: dict = None) -> int:
		units = {
			"s": self.sector,
			"sector": self.sector,
			"sectors": self.sector
		}
		if alt_units:
			units.update(alt_units)
		return size_to_bytes(value, units)

	def size_to_sectors(self, value: str | int, alt_units: dict = None) -> int:
		ret = self.size_to_bytes(value, alt_units)
		return ceil(ret / self.sector)

	def _parse_area(self, config: dict) -> Area:
		start, end, size = -1, -1, -1
		if "start" in config: start = self.size_to_sectors(config["start"])
		if "offset" in config: start = self.size_to_sectors(config["offset"])
		if "end" in config: end = self.size_to_sectors(config["end"])
		if "size" in config: size = self.size_to_sectors(config["size"])
		if "length" in config: size = self.size_to_sectors(config["length"])
		if "start_lba" in config: start = config["start_lba"]
		if "offset_lba" in config: start = config["offset_lba"]
		if "end_lba" in config: end = config["end_lba"]
		if "size_lba" in config: size = config["size_lba"]
		if "length_lba" in config: size = config["length_lba"]
		return Area(start, end, size)

	def parse_area(self, config: dict) -> Area:
		area = self._parse_area(config)
		area.fixup()
		return area

	def parse_free_area(self, config: dict) -> Area:
		return self.find_free_area(area=self._parse_area(config))

	def resort_partitions(self):
		self.partitions.sort(key=lambda p: p.start_lba)
		idx = 0
		for part in self.partitions:
			part.idx = idx
			idx += 1

	def add_partition_from(self, config: dict) -> DiskPart:
		area = self.parse_free_area(config)
		if area is None: raise ValueError("no free area found")
		ptype = config["ptype"] if "ptype" in config else "linux"
		return self.add_partition(ptype, area=area)

	def del_partition(self, part: DiskPart):
		if part not in self.partitions:
			if part.layout == self:
				raise ValueError("removed partition")
			raise KeyError("partition not found")
		self.partitions.remove(part)

	def add_partition(
		self,
		ptype: str = None,
		start: int = -1,
		end: int = -1,
		size: int = -1,
		area: Area = None,
	) -> DiskPart: pass

	def __init__(
		self,
		fp: RawIOBase = None,
		path: str = None,
		sector: int = 512
	):
		DiskIO.__init__(self)
		self.partitions = []
		self.loaded = False
		self._sector = sector
		if sector < self._min_sector:
			raise ValueError("bad sector size")
		if fp: self._fp = fp
		elif path:
			self._fp = open(path, "wb+")
			self._opened = True
		else: raise ValueError("no I/O interface")

	def __del__(self):
		if self._opened: self._fp.close()

	def __len__(self) -> int:
		return len(self.partitions)

	def __setitem__(self, key: int, value: DiskPart):
		self.resort_partitions()
		self.partitions[key] = value

	def __getitem__(self, key: int) -> DiskPart:
		self.resort_partitions()
		return self.partitions[key]

	def __delitem__(self, key: int):
		self.resort_partitions()
		self.del_partition(self.partitions[key])
		self.resort_partitions()

	def __iadd__(self, value: DiskPart) -> DiskPart:
		self.resort_partitions()
		value.idx = len(self.partitions)
		self.partitions += value
		self.resort_partitions()
		return value
