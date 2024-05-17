from typing import Self
from builder.lib.utils import round_up, round_down, size_to_bytes
from builder.lib.serializable import SerializableDict, SerializableList


class Area(SerializableDict):
	start: int = -1
	end: int = -1
	size: int = -1

	def set(self, start: int = -1, end: int = -1, size: int = -1) -> Self:
		self.start, self.end, self.size = start, end, size
		return self

	def to_tuple(self) -> tuple[int, int, int]:
		return self.start, self.end, self.size

	def to_dict(self) -> dict:
		return {
			"start": self.start,
			"end": self.end,
			"size": self.size,
		}

	def reset(self) -> Self:
		self.set(-1, -1, -1)
		return self

	def from_dict(self, o: dict) -> Self:
		self.reset()
		if "start" in o: self.start = size_to_bytes(o["start"])
		if "offset" in o: self.start = size_to_bytes(o["offset"])
		if "end" in o: self.end = size_to_bytes(o["end"])
		if "size" in o: self.size = size_to_bytes(o["size"])
		if "length" in o: self.size = size_to_bytes(o["length"])
		return self

	def is_area_in(self, area: Self) -> bool:
		self.fixup()
		area.fixup()
		return (
			(self.start <= area.start <= self.end) and
			(self.start <= area.end <= self.end) and
			(area.size <= self.size)
		)

	def fixup(self) -> Self:
		if self.start >= 0 and self.end >= 0 and self.start > self.end + 1:
			raise ValueError("start large than end")
		if 0 <= self.end < self.size and self.size >= 0:
			raise ValueError("size large than end")
		if self.start >= 0 and self.end >= 0 and self.size >= 0:
			if self.size != self.end - self.start + 1:
				raise ValueError("bad size")
		elif self.start >= 0 and self.end >= 0:
			self.size = self.end - self.start + 1
		elif self.start >= 0 and self.size >= 0:
			self.end = self.start + self.size - 1
		elif self.end >= 0 and self.size >= 0:
			self.start = self.end - self.size + 1
		else:
			raise ValueError("missing value")
		return self

	def __init__(self, start: int = -1, end: int = -1, size: int = -1, area: Self = None):
		super().__init__()
		if area: start, end, size = area.to_tuple()
		self.start, self.end, self.size = start, end, size


def convert(start: int = -1, end: int = -1, size: int = -1, area: Area = None) -> Area:
	return Area(start, end, size, area).fixup()


def to_tuple(start: int = -1, end: int = -1, size: int = -1, area: Area = None) -> tuple[int, int, int]:
	return convert(start, end, size, area).to_tuple()


class Areas(list[Area], SerializableList):
	def is_area_in(self, area: Area) -> bool:
		return any(pool.is_area_in(area) for pool in self)

	def merge(self) -> Self:
		idx = 0
		self.sort(key=lambda x: (x.start, x.end))
		while len(self) > 0:
			curr = self[idx]
			if curr.size <= 0:
				self.remove(curr)
				continue
			if idx > 0:
				last = self[idx - 1]
				if last.end + 1 >= curr.start:
					ent = Area(last.start, curr.end)
					ent.fixup()
					self.remove(last)
					self.remove(curr)
					self.insert(idx - 1, ent)
					idx -= 1
			idx += 1
			if idx >= len(self): break
		return self

	def lookup(
		self,
		start: int = -1,
		end: int = -1,
		size: int = -1,
		area: Area = None,
	) -> Area | None:
		start, end, size = to_tuple(start, end, size, area)
		for area in self:
			if not (area.start <= start <= area.end): continue
			if not (area.start <= end <= area.end): continue
			if size > area.size: continue
			return area
		return None

	def align(self, align: int) -> Self:
		self.sort(key=lambda x: (x.start, x.end))
		for area in self:
			start = round_up(area.start, align)
			end = round_down(area.end + 1, align) - 1
			size = end - start + 1
			if start >= end or size < align:
				self.remove(area)
			else:
				area.set(start, end, size)
		self.merge()
		return self

	def add(
		self,
		start: int = -1,
		end: int = -1,
		size: int = -1,
		area: Area = None
	) -> Area | None:
		if area: start, end, size = area.to_tuple()
		cnt = (start >= 0) + (end >= 0) + (size >= 0)
		if cnt < 2: raise ValueError("missing value")
		r = convert(start, end, size)
		if r.size <= 0: return None
		self.append(r)
		return r

	def splice(
		self,
		start: int = -1,
		end: int = -1,
		size: int = -1,
		area: Area = None,
	) -> bool:
		start, end, size = to_tuple(start, end, size, area)
		if len(self) <= 0: return False
		rs = min(area.start for area in self)
		re = max(area.end for area in self)
		if start < rs: start = rs
		if end > re: end = re
		start, end, size = to_tuple(start, end)
		target = self.lookup(start, end, size)
		if target is None: return False
		self.remove(target)
		self.add(target.start, start - 1)
		self.add(end + 1, target.end)
		self.merge()
		return True

	def find(
		self,
		start: int = -1,
		end: int = -1,
		size: int = -1,
		area: Area = None,
		biggest: bool = True,
	) -> Area | None:
		if area: start, end, size = area.to_tuple()
		cnt = (start >= 0) + (end >= 0) + (size >= 0)
		if cnt >= 2:
			area = convert(start, end, size)
			return area if self.is_area_in(area) else None
		use = Areas()
		for free in self:
			if start >= 0 and not (free.start <= start <= free.end): continue
			if end >= 0 and not (free.start <= end <= free.end): continue
			if size >= 0 and size > free.size: continue
			use.add(area=free)
		if biggest: use.sort(key=lambda x: x.size)
		if len(use) <= 0: return None
		target = use[0]
		if start >= 0: target.start, target.end = start, -1
		if end >= 0: target.start, target.end = -1, end
		if size >= 0: target.end, target.size = -1, size
		return target.fixup()

	def to_list(self) -> list:
		return self

	def from_list(self, o: list) -> Self:
		self.clear()
		for i in o: self.append(Area().from_dict(i))
		return self
