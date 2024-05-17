from builder.lib.area import Area, Areas


class DiskArea:
	def find_free_area(
		self,
		start: int = -1,
		end: int = -1,
		size: int = -1,
		area: Area = None,
		biggest: bool = True,
	) -> Area:
		return self.get_free_areas().find(
			start, end, size, area, biggest
		)

	def get_free_size(self) -> int:
		return sum(area.size for area in self.get_free_areas())

	def get_usable_area(self) -> Area:
		pass

	def get_used_areas(self, table=False) -> Areas:
		pass

	def get_free_areas(self) -> Areas:
		pass
