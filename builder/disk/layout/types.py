
class DiskTypes:
	@staticmethod
	def lookup(t) -> list[tuple[int, str]]:
		pass

	def lookup_one(t) -> tuple[int, str]:
		l = DiskTypes.lookup(t)
		return l[0] if len(l) > 0 else None

	@staticmethod
	def lookup_one_id(t) -> int:
		r = DiskTypes.lookup_one(t)
		return r[0] if r else None

	@staticmethod
	def lookup_one_name(t) -> str:
		r = DiskTypes.lookup_one(t)
		return r[1] if r else None

	@staticmethod
	def lookup_names(t) -> list[str]:
		r = DiskTypes.lookup(t)
		return [t[1] for t in r]

	@staticmethod
	def equal(l, r) -> bool:
		lf = DiskTypes.lookup_one_id(l)
		rf = DiskTypes.lookup_one_id(r)
		if lf is None or rf is None: return False
		return lf == rf

	types: list[tuple[int, str]] = []
