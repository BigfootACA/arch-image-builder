from os import urandom
from io import RawIOBase
from logging import getLogger
from builder.lib.area import Area, Areas
from builder.disk.layout.layout import DiskLayout
from builder.disk.layout.mbr.types import DiskTypesMBR
from builder.disk.layout.mbr.struct import MasterBootRecord, MbrPartEntry
from builder.disk.layout.mbr.part import DiskPartMBR
log = getLogger(__name__)


class DiskLayoutMBR(DiskLayout):
	boot_code: bytes
	mbr_id: int
	partitions: list[DiskPartMBR]

	@property
	def id(self) -> str:
		return f"{self.mbr_id:08x}"

	@id.setter
	def id(self, val: str):
		self.mbr_id = int(val, base=16)

	def del_partition(self, part: DiskPartMBR):
		DiskLayout.del_partition(self, part)
		if DiskTypesMBR.equal(part, "extended") and not part.logical:
			parts = [p for p in self.partitions if p.extend == part]
			for p in parts: self.del_partition(p)

	def add_partition(
		self,
		ptype: int | str = None,
		start: int = -1,
		end: int = -1,
		size: int = -1,
		area: Area = None,
		logical: bool | None = None,
		aligned: bool = True,
	) -> DiskPartMBR | None:
		area = self.find_free_area(start, end, size, area, aligned=aligned)
		if area is None: return None
		if ptype is None: ptype = "linux"
		extend: DiskPartMBR | None = None
		ps = self.partitions
		tid = DiskTypesMBR.lookup_one_id("extended")
		primary: list[DiskPartMBR] = [p for p in ps if not p.logical]
		extended: list[DiskPartMBR] = [p for p in ps if p.type_id == tid]
		if logical is None: logical = len(primary) >= 4
		if logical:
			if extended is None: raise RuntimeError("no extended table")
			if DiskTypesMBR.equal(ptype, "extended"):
				raise ValueError("attempt add extended table as logical")
			extend = next((e.to_area().is_area_in(area) for e in extended), None)
			if extend is None: raise ValueError(
				"logical partition out of extended table"
			)
		elif len(primary) >= 4:
			raise ValueError("no space for primary partition")
		self.resort_partitions()
		idx = len(self.partitions)
		item = MbrPartEntry()
		item.set_start_lba(area.start)
		item.set_size_lba(area.end)
		item.set_type(ptype)
		part = DiskPartMBR(self, item, idx)
		if logical: part.extend = extend
		self.partitions.insert(idx, part)
		pl = "logical" if logical else "primary"
		log.debug(
			f"Added {pl} partition {idx} "
			f"start LBA {area.start} "
			f"end LBA {area.end} "
			f"type {ptype}"
		)
		return part

	def add_partition_from(self, config: dict) -> DiskPartMBR:
		aligned = config["aligned"] if "aligned" in config else True
		area = self.parse_free_area(config, aligned=aligned)
		if area is None: raise ValueError("no free area found")
		ptype = config["ptype"] if "ptype" in config else None
		logical = config["logical"] if "logical" in config else None
		part = self.add_partition(ptype, area=area, logical=logical, aligned=aligned)
		if part:
			if "bootable" in config:
				part.bootable = config["bootable"]
		return part

	def get_usable_area(self, aligned=True) -> Area | None:
		if self.total_lba <= 2: return None
		end = self.total_lba - 1
		start = min(self.align_lba, end) if aligned else 1
		return Area(start=start, end=end).fixup()

	def get_used_areas(self, table=False) -> Areas:
		areas = Areas()
		if table: areas.add(start=1, size=1)
		for part in self.partitions:
			if part.size_lba <= 0: continue
			start, size = part.start_lba, part.size_lba
			if part.logical and table: size += 1
			if DiskTypesMBR.equal(part, "extended"):
				if not table: continue
				size = 1
			areas.add(start=start, size=size)
		areas.merge()
		return areas

	def get_free_areas(self, aligned=True) -> Areas:
		areas = Areas()
		usable = self.get_usable_area(aligned=aligned)
		if usable is None: return areas
		areas.add(area=usable)
		for part in self.partitions:
			start = part.start_lba
			end = part.end_lba
			size = part.size_lba
			if DiskTypesMBR.equal(part, "extended"):
				end = -1
				size = 1
			elif part.logical:
				end += 1
				size += 1
			areas.splice(start, end, size)
		if aligned:
			areas.align(self.align_lba)
		return areas

	def create_mbr(self) -> MasterBootRecord:
		new_mbr = MasterBootRecord()
		new_mbr.fill_header()
		if self.boot_code:
			new_mbr.boot_code = self.boot_code
		new_mbr.mbr_id = self.mbr_id
		idx = 0
		for part in self.partitions:
			if part.logical: continue
			if idx >= 4: raise RuntimeError("too many primary partitions")
			new_mbr.partitions[idx] = part.to_entry()
			idx += 1
		return new_mbr

	def write_header(self):
		if not self._fp.writable():
			raise IOError("write is not allow")
		mbr = self.create_mbr()
		self.write_table(mbr, 0)
		ebr = self.create_ebr_chains()
		for sector in ebr:
			self.write_table(ebr[sector], sector)
		self._fp.flush()
		log.info("MBR partition table saved")

	def try_load_mbr(self) -> MasterBootRecord | None:
		mbr_data = self.read_lba(0)
		mbr = MasterBootRecord.from_buffer_copy(mbr_data)
		if not mbr.check_signature():
			log.debug("Bad MBR")
			return None
		self.mbr_id = mbr.mbr_id
		self.boot_code = mbr.boot_code
		log.debug(f"Found MBR id {self.id}")
		return mbr

	def try_load_mbr_extended_entries(self, ext: DiskPartMBR) -> list[DiskPartMBR] | None:
		extends: list[DiskPartMBR] = []
		ebr_data = self.read_lba(ext.start_lba)
		ebr = MasterBootRecord.from_buffer_copy(ebr_data)
		if not ebr.check_signature():
			if ebr.signature == 0:
				log.debug("Empty EBR")
				return extends
			log.debug("Bad EBR")
			return None
		for item in ebr.partitions:
			idx = len(self.partitions)
			part = DiskPartMBR(self, item, idx)
			if part.size_lba == 0: continue
			part.extend = ext.get_root_ebr()
			part.logical = True
			if DiskTypesMBR.equal(part.type_id, "extended"):
				part.start_lba += part.extend.start_lba
				extends.append(part)
			else:
				part.start_lba += ext.start_lba
				self.partitions.insert(idx, part)
			log.debug(
				f"Found logical partition {idx} "
				f"start LBA {part.start_lba} "
				f"end LBA {part.end_lba} "
				f"type {part.type}"
			)
		return extends

	def try_load_mbr_entries(self, mbr: MasterBootRecord) -> bool:
		ret = True
		nested: list[DiskPartMBR] = []
		extends: list[DiskPartMBR] = []
		self.partitions.clear()
		log.debug("Try loading MBR primary partitions")
		for item in mbr.partitions:
			if item.size_lba == 0: continue
			idx = len(self.partitions)
			part = DiskPartMBR(self, item, idx)
			if DiskTypesMBR.equal(part.type_id, "extended"):
				extends.append(part)
			self.partitions.insert(idx, part)
			log.debug(
				f"Found primary partition {idx} "
				f"start LBA {part.start_lba} "
				f"end LBA {part.end_lba} "
				f"type {part.type}"
			)
		while len(extends) > 0:
			for extend in extends:
				log.debug(
					"Try loading MBR logical partitions from "
					f"LBA {extend.start_lba}"
				)
				ne = self.try_load_mbr_extended_entries(extend)
				if ne is None: ret = False
				else: nested.extend(ne)
			extends = nested
			nested = []
		cnt = len(self.partitions)
		if ret: log.debug(f"Found {cnt} partitions")
		return ret

	def create_ebr_chains(self) -> dict[int: MasterBootRecord]:
		for part in self.partitions:
			if part.logical:
				raise RuntimeError("EBR generate does not implemented now")
		return {}

	def load_header(self) -> bool:
		self.unload()
		mbr = self.try_load_mbr()
		if mbr is None: return False
		if not self.try_load_mbr_entries(mbr): return False
		self.loaded = True
		return True

	def unload(self):
		self.loaded = False
		self.mbr_id = 0
		self.boot_code = bytes()
		self.partitions.clear()

	def reload(self):
		if self.load_header(): return
		raise IOError("Load MBR header failed")

	def create(self):
		self.unload()
		self.mbr_id = int.from_bytes(urandom(4))

	def set_from(self, config: dict):
		if "id" in config: self.mbr_id = int(config["id"])

	def to_dict(self) -> dict:
		return {
			"id": self.id,
			"mbr_id": self.mbr_id,
			"sector": self.sector,
			"sectors": self.total_lba,
			"size": self.total_size,
			"free": self.get_free_size(),
			"partitions": self.partitions,
			"usable_area": self.get_usable_area(),
			"free_area": self.get_free_areas(),
		}

	def __init__(
		self,
		fp: RawIOBase = None,
		path: str = None,
		sector: int = 512
	):
		super().__init__(fp=fp, path=path, sector=sector)
		self.partitions = []
		self.mbr_id = 0
		self.boot_code = bytes()
		self.load_header()
