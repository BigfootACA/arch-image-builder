from logging import getLogger
from builder.disk.layout.types import DiskTypes
log = getLogger(__name__)


class DiskTypesMBR(DiskTypes):
	@staticmethod
	def lookup(t) -> list[tuple[int, str]]:
		ret: list[tuple[int, str]] = []
		ts = DiskTypesMBR.types
		from builder.disk.layout.mbr.struct import MbrPartEntry
		from builder.disk.layout.mbr.part import DiskPartMBR
		if isinstance(t, DiskPartMBR):
			u = t.type_id
		elif isinstance(t, MbrPartEntry):
			u = int(t.os_indicator)
		elif type(t) is int:
			u = t
		elif type(t) is str:
			ret = [tn for tn in ts if tn[1] == t]
			if len(ret) > 0: return ret
			try: u = int(t)
			except: return ret
		else: return ret
		return [tn for tn in ts if tn[0] == u]

	def lookup_one(t) -> tuple[int, str]:
		l = DiskTypesMBR.lookup(t)
		return l[0] if len(l) > 0 else None

	@staticmethod
	def lookup_one_id(t) -> int:
		r = DiskTypesMBR.lookup_one(t)
		return r[0] if r else 0

	@staticmethod
	def lookup_one_name(t) -> str:
		r = DiskTypesMBR.lookup_one(t)
		return r[1] if r else None

	@staticmethod
	def lookup_names(t) -> list[str]:
		r = DiskTypesMBR.lookup(t)
		return [t[1] for t in r]

	@staticmethod
	def equal(l, r) -> bool:
		lf = DiskTypesMBR.lookup_one_id(l)
		rf = DiskTypesMBR.lookup_one_id(r)
		if lf == 0 or rf == 0: return False
		return lf == rf

	types: list[tuple[int, str]] = [
		(0x01, "fat12"),
		(0x05, "extended"),
		(0x06, "fat16"),
		(0x07, "ntfs"),
		(0x07, "exfat"),
		(0x07, "hpfs"),
		(0x0b, "fat32"),
		(0x0f, "extended-lba"),
		(0x16, "hidden-fat16"),
		(0x17, "hidden-ntfs"),
		(0x17, "hidden-exfat"),
		(0x17, "hidden-hpfs"),
		(0x1b, "hidden-fat32"),
		(0x81, "minix"),
		(0x82, "linux-swap"),
		(0x83, "linux"),
		(0x85, "linux-extended"),
		(0x85, "linuxex"),
		(0x88, "linux-plaintext"),
		(0x8e, "linux-lvm"),
		(0xa5, "freebsd"),
		(0xa6, "openbsd"),
		(0xa9, "netbsd"),
		(0xaf, "hfs"),
		(0xea, "linux-boot"),
		(0xee, "gpt"),
		(0xef, "efi"),
		(0xef, "uefi"),
		(0xef, "esp"),
		(0xfd, "linux-raid"),
	]
