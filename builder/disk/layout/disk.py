from io import RawIOBase
from builder.disk.layout.layout import DiskLayout
from builder.disk.layout.mbr.layout import DiskLayoutMBR
from builder.disk.layout.gpt.layout import DiskLayoutGPT


class Disk:
	layouts: list[tuple[type[DiskLayout], list[str]]] = [
		(DiskLayoutGPT, ["gpt", "guid", "efi", "uefi"]),
		(DiskLayoutMBR, ["mbr", "bios", "legacy", "msdos", "dos"]),
	]

	@staticmethod
	def probe_layout(
		fp: RawIOBase = None,
		path: str = None,
		sector: int = 512,
		fallback: str | type[DiskLayout] = None,
	) -> DiskLayout | None:
		for layout in Disk.layouts:
			d = layout[0](fp, path, sector)
			if d.loaded: return d
		if fallback:
			if type(fallback) is str:
				fallback = Disk.find_layout(fallback)
			if type(fallback) is type[DiskLayout]:
				d = fallback(fp, path, sector)
				if d.loaded: return d
		return None

	@staticmethod
	def find_layout(name: str) -> type[DiskLayout]:
		return next((
			layout[0]
			for layout in Disk.layouts
			if name in layout[1]
		), None)
