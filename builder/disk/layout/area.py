from builder.lib.area import Area, Areas


class DiskArea:
	def find_free_area(
		self,
		start: int = -1,
		end: int = -1,
		size: int = -1,
		area: Area = None,
		biggest: bool = True,
		aligned: bool = True,
	) -> Area:
		return self.get_free_areas(aligned=aligned).find(
			start, end, size, area, biggest
		)

	def get_free_size(self, aligned=True) -> int:
		return sum(area.size for area in self.get_free_areas(aligned=aligned))

	def get_usable_area(self, aligned=True) -> Area:
		pass

	def get_used_areas(self, table=False) -> Areas:
		pass

	def get_free_areas(self, aligned=True) -> Areas:
		pass
