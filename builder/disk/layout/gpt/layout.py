import ctypes
from io import RawIOBase
from uuid import UUID, uuid4
from ctypes import sizeof
from binascii import crc32
from logging import getLogger
from builder.lib.area import Area, Areas
from builder.lib.utils import bytes_pad, round_up, round_down
from builder.disk.layout.layout import DiskLayout
from builder.disk.layout.mbr.types import DiskTypesMBR
from builder.disk.layout.mbr.struct import MasterBootRecord, MbrPartEntry
from builder.disk.layout.gpt.struct import EfiPartTableHeader, EfiPartEntry
from builder.disk.layout.gpt.types import DiskTypesGPT
from builder.disk.layout.gpt.uefi import EfiGUID
from builder.disk.layout.gpt.part import DiskPartGPT
log = getLogger(__name__)


NULL_UUID = UUID("00000000-0000-0000-0000-000000000000")


class DiskLayoutGPT(DiskLayout):
	boot_code: bytes
	uuid: UUID
	main_entries_lba: int
	entries_count: int
	partitions: list[DiskPartGPT]

	@property
	def id(self) -> str:
		return str(self.uuid)

	@id.setter
	def id(self, val: str):
		self.uuid = UUID(val)

	@property
	def entries_size(self) -> int:
		return self.entries_count * sizeof(EfiPartEntry)

	@property
	def entries_sectors(self) -> int:
		return self.entries_size // self.sector

	@property
	def backup_entries_lba(self) -> int:
		return self.total_lba - self.entries_sectors - 1

	@property
	def main_entries(self) -> Area:
		return Area(
			start=self.main_entries_lba,
			size=self.entries_sectors
		).fixup()

	@property
	def backup_entries(self) -> Area:
		return Area(
			start=self.backup_entries_lba,
			size=self.entries_sectors
		).fixup()

	def add_partition(
		self,
		ptype: str | UUID = None,
		start: int = -1,
		end: int = -1,
		size: int = -1,
		area: Area = None,
		name: str = None,
		uuid: UUID = None,
	) -> DiskPartGPT | None:
		area = self.find_free_area(start, end, size, area)
		if area is None: return None
		if ptype is None: ptype = "linux"
		t = DiskTypesGPT.lookup_one_uuid(ptype)
		if t is None: raise ValueError(f"unknown type {ptype}")
		self.resort_partitions()
		idx = len(self.partitions)
		part = DiskPartGPT(self, None, idx)
		part.start_lba = area.start
		part.end_lba = area.end
		part.type_uuid = t
		part.uuid = uuid or uuid4()
		part.part_name = name or ""
		self.partitions.insert(idx, part)
		log.info(
			f"Added partition {idx} "
			f"start LBA {area.start} "
			f"end LBA {area.end} "
			f"type {ptype}"
		)
		return part

	def add_partition_from(self, config: dict) -> DiskPartGPT:
		area = self.parse_free_area(config)
		if area is None: raise ValueError("no free area found")
		ptype = config["ptype"] if "ptype" in config else None
		pname = config["pname"] if "pname" in config else None
		puuid = UUID(config["puuid"]) if "puuid" in config else None
		part = self.add_partition(ptype, area=area, name=pname, uuid=puuid)
		if part:
			if "hybrid" in config:
				part.hybrid = True
			if "bootable" in config:
				part.bootable = True
			if "attributes" in config:
				part.attributes = config["attributes"]
		return part

	def get_usable_area(self) -> Area | None:
		if self.main_entries_lba < 2: return None
		if self.entries_count <= 0: return None
		start = 2
		end = round_down(self.backup_entries_lba, self.align_lba)
		rs = min((part.start_lba for part in self.partitions), default=end)
		first = self.main_entries_lba + self.entries_sectors + 1
		if len(self.partitions) == 0 or first <= rs: start = first
		start = round_up(start, self.align_lba)
		return Area(start=start, end=end - 1).fixup()

	def get_used_areas(self, table=False) -> Areas:
		areas = Areas()
		if table:
			areas.add(start=0, size=2)
			areas.add(area=self.main_entries)
			areas.add(area=self.backup_entries)
			areas.add(start=self.total_lba - 1, size=1)
		for part in self.partitions:
			areas.add(area=part.to_area())
		areas.merge()
		return areas

	def get_free_areas(self) -> Areas:
		areas = Areas()
		usable = self.get_usable_area()
		if usable is None: return areas
		areas.add(area=usable)
		for part in self.partitions:
			areas.splice(area=part.to_area())
		areas.align(self.align_lba)
		return areas

	def try_load_pmbr(self) -> MasterBootRecord | None:
		pmbr_data = self.read_lba(0)
		pmbr = MasterBootRecord.from_buffer_copy(pmbr_data)
		if not pmbr.check_signature():
			log.debug("Bad protective MBR")
			return None
		self.boot_code = pmbr.boot_code
		return pmbr

	def get_pmbr_entry(self, pmbr: MasterBootRecord) -> MbrPartEntry | None:
		if pmbr is None: return None
		ps = pmbr.partitions
		tid = DiskTypesMBR.lookup_one_id("gpt")
		return next((part for part in ps if part.type_id == tid), None)

	def try_load_entries(self, gpt: EfiPartTableHeader) -> bool:
		if gpt is None: return False
		es = sizeof(EfiPartEntry)
		if gpt.entry_size != es:
			log.debug("Unsupported GPT entry size")
			log.debug(f"size {es} != {gpt.entry_size}")
			return False
		size = gpt.entries_count * gpt.entry_size
		sectors = size // self.sector
		if size % self.sector != 0:
			log.debug("GPT entries size misaligned with sector size")
			sectors += 1
		parts = self.read_lbas(gpt.part_entry_lba, sectors)
		crc = crc32(parts[0:size], 0)
		if crc != gpt.entries_crc32:
			log.debug("GPT entries crc32 mismatch")
			log.debug(f"crc32 {crc} != {gpt.entries_crc32}")
			return False
		self.partitions.clear()
		for idx in range(gpt.entries_count):
			start = idx * gpt.entry_size
			size = min(es, gpt.entry_size)
			data = parts[start:start + size]
			entry = EfiPartEntry.from_buffer_copy(data)
			if entry.type_guid.to_uuid() == NULL_UUID: continue
			idx = len(self.partitions)
			part = DiskPartGPT(self, entry, idx)
			self.partitions.insert(idx, part)
			log.debug(
				f"Found partition {idx} "
				f"start LBA {part.start_lba} "
				f"end LBA {part.end_lba} "
				f"name {part.part_name} "
			)
		self.uuid = gpt.disk_guid.to_uuid()
		self.main_entries_lba = gpt.part_entry_lba
		self.entries_count = gpt.entries_count
		log.info("Found %d partitions in GPT", len(self.partitions))
		return True

	def try_load_lba(self, lba: int) -> EfiPartTableHeader:
		log.debug(f"Try GPT at LBA {lba}")
		gpt_data = self.read_lba(lba)
		gpt = EfiPartTableHeader.from_buffer_copy(gpt_data)
		if gpt and gpt.check_header():
			log.debug(f"Loaded GPT at LBA {lba}")
		else:
			log.debug(f"Bad GPT at LBA {lba}")
			gpt = None
		return gpt

	def try_load_gpt(self, pmbr: MasterBootRecord) -> bool:
		lba = -1
		pent = self.get_pmbr_entry(pmbr)
		if pent:
			lba = pent.start_lba
			gpt = self.try_load_lba(lba)
			if self.try_load_entries(gpt): return True
		if lba != 1:
			lba = 1
			gpt = self.try_load_lba(lba)
			if self.try_load_entries(gpt): return True
		log.debug("Main GPT table unavailable")
		lba = -1
		if pent:
			lba = pent.size_lba - 1
			gpt = self.try_load_lba(lba)
			if self.try_load_entries(gpt): return True
		last = self.total_lba - 1
		if lba != last:
			lba = 1
			gpt = self.try_load_lba(last)
			if self.try_load_entries(gpt): return True
		log.debug("Backup GPT table unavailable")
		return False

	def load_header(self) -> bool:
		self.unload()
		pmbr = self.try_load_pmbr()
		if pmbr:
			pent = self.get_pmbr_entry(pmbr)
			if pent is None:
				log.debug("GPT not found in PMBR")
				return False
		if not self.try_load_gpt(pmbr): return False
		log.info("GPT partition tables loaded")
		self.loaded = True
		return True

	def create_pmbr(self) -> MasterBootRecord:
		new_pmbr = MasterBootRecord()
		new_pmbr.fill_header()
		if self.boot_code:
			size = MasterBootRecord.boot_code.size
			code = bytes_pad(self.boot_code, size, trunc=True)
			ctypes.memmove(new_pmbr.boot_code, code, size)
		idx = 0
		for part in self.partitions:
			if not part.hybrid: continue
			if idx >= 3: raise RuntimeError("Hybrid partition to many")
			ppart = part.to_mbr_entry()
			new_pmbr.partitions[idx] = ppart
			idx += 1
		ppart = MbrPartEntry()
		ppart.start_lba = 1
		ppart.size_lba = self.total_lba - 1
		ppart.start_head, ppart.start_track, ppart.start_sector = 0, 0, 2
		ppart.end_head, ppart.end_track, ppart.end_sector = 255, 255, 255
		ppart.set_type("gpt")
		new_pmbr.partitions[idx] = ppart
		return new_pmbr

	def create_gpt_entries(self) -> bytes:
		es = sizeof(EfiPartEntry)
		ec = self.entries_count if self.entries_count > 0 else 128
		if len(self.partitions) > ec:
			raise OverflowError("too many partitions")
		self.resort_partitions()
		data = bytes().join(
			part.to_entry()
			for part in self.partitions
			if part.type_uuid != NULL_UUID
		)
		if len(data) > ec * es:
			raise OverflowError("partitions buffer too big")
		return bytes_pad(data, ec * es)

	def create_gpt_head(
		self,
		entries: bytes,
		backup: bool = False
	) -> EfiPartTableHeader:
		if self.total_lba < 128:
			raise ValueError("disk too small")
		new_gpt = EfiPartTableHeader()
		new_gpt.fill_header()
		new_gpt.entry_size = sizeof(EfiPartEntry)
		new_gpt.entries_count = self.entries_count
		new_gpt.disk_guid = EfiGUID.from_uuid(self.uuid)
		le = len(entries)
		if le != new_gpt.entries_count * new_gpt.entry_size:
			raise ValueError("entries size mismatch")
		if le % self.sector != 0:
			raise ValueError("bad entries size")
		entries_sectors = le // self.sector
		if entries_sectors != self.entries_sectors:
			raise ValueError("entries sectors mismatch")
		usable = self.get_usable_area()
		new_gpt.first_usable_lba = usable.start
		new_gpt.last_usable_lba = usable.end
		if backup:
			new_gpt.part_entry_lba = self.backup_entries_lba
			new_gpt.current_lba = self.total_lba - 1
			new_gpt.alternate_lba = 1
		else:
			new_gpt.part_entry_lba = self.main_entries_lba
			new_gpt.current_lba = 1
			new_gpt.alternate_lba = self.total_lba - 1
		new_gpt.entries_crc32 = crc32(entries)
		new_gpt.header.update_crc32(bytes(new_gpt))
		return new_gpt

	def recreate_header(self) -> dict:
		new_pmbr = self.create_pmbr()
		if new_pmbr is None: raise RuntimeError("generate pmbr failed")
		log.debug(f"Protective MBR: {new_pmbr}")
		new_gpt_entries = self.create_gpt_entries()
		if new_gpt_entries is None: raise RuntimeError("generate gpt entries failed")
		new_gpt_main = self.create_gpt_head(new_gpt_entries, backup=False)
		if new_gpt_main is None: raise RuntimeError("generate gpt main head failed")
		log.debug(f"GPT Main head: {new_gpt_main}")
		new_gpt_back = self.create_gpt_head(new_gpt_entries, backup=True)
		if new_gpt_back is None: raise RuntimeError("generate gpt backup head failed")
		log.debug(f"GPT Backup head: {new_gpt_back}")
		return {
			"pmbr": new_pmbr,
			"main": new_gpt_main,
			"backup": new_gpt_back,
			"entries": new_gpt_entries,
		}

	def write_table(self, table, lba: int):
		data = bytes(table)
		size = round_up(len(data), self.sector)
		data = bytes_pad(data, size)
		sectors = size // self.sector
		area = Area(start=lba, size=sectors)
		if self.get_used_areas().is_area_in(area):
			raise RuntimeError("attempt write table into partition")
		log.debug(f"Wrote {len(data)} bytes to LBA {lba} with {sectors} sectors")
		self.write_lbas(lba, data, sectors)

	def write_header(self):
		if not self._fp.writable():
			raise IOError("write is not allow")
		data = self.recreate_header()
		self.write_table(data["pmbr"], 0)
		self.write_table(data["main"], data["main"].current_lba)
		self.write_table(data["backup"], data["backup"].current_lba)
		self.write_table(data["entries"], data["main"].part_entry_lba)
		self.write_table(data["entries"], data["backup"].part_entry_lba)
		self._fp.flush()
		log.info("GPT partition table saved")

	def unload(self):
		self.boot_code = bytes()
		self.uuid = uuid4()
		self.main_entries_lba = 2
		self.entries_count = 128
		self.loaded = False
		self.partitions.clear()

	def reload(self):
		if not self.load_header():
			raise IOError("Load GPT header failed")

	def save(self):
		self.write_header()

	def create(self):
		self.unload()
		log.info("Created new GPT partition table")

	def set_from(self, config: dict):
		if "uuid" in config: self.uuid = UUID(config["uuid"])
		if "entries_offset" in config:
			self.main_entries_lba = self.size_to_sectors(config["entries_lba"])
		if "entries_lba" in config:
			self.main_entries_lba = config["entries_lba"]
		if "entries_count" in config:
			self.entries_count = config["entries_count"]

	def to_dict(self) -> dict:
		return {
			"uuid": self.uuid,
			"free": self.get_free_size(),
			"sector": self.sector,
			"sectors": self.total_lba,
			"size": self.total_size,
			"partitions": self.partitions,
			"usable_area": self.get_usable_area(),
			"free_area": self.get_free_areas(),
			"entries_count": self.entries_count,
			"main_entries": self.main_entries,
			"backup_entries": self.backup_entries,
		}

	def __init__(self, fp: RawIOBase = None, path: str = None, sector: int = 512):
		super().__init__(fp=fp, path=path, sector=sector)
		self.boot_code = bytes()
		self.uuid = NULL_UUID
		self.main_entries_lba = -1
		self.entries_count = -1
		self.partitions = []
		self.load_header()
