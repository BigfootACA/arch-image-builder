from typing import Self


class Serializable:
	def serialize(self) -> None | bool | int | float | str | tuple | list | dict: pass
	def unserialize(self, value: None | bool | int | float | str | tuple | list | dict): pass

	def to_json(
		self, *,
		skipkeys=False,
		ensure_ascii=True,
		check_circular=True,
		allow_nan=True,
		cls=None,
		indent=None,
		separators=None,
		default=None,
		sort_keys=False,
		**kw
	) -> str:
		from builder.lib.json import dumps
		return dumps(
			self.serialize(),
			skipkeys=skipkeys,
			ensure_ascii=ensure_ascii,
			check_circular=check_circular,
			allow_nan=allow_nan,
			cls=cls,
			indent=indent,
			separators=separators,
			default=default,
			sort_keys=sort_keys,
			**kw
		)

	def to_yaml(self) -> str:
		from yaml import safe_dump_all
		return safe_dump_all(self.serialize())

	@property
	def class_path(self) -> str:
		ret = self.__class__.__module__ or ""
		if len(ret) > 0: ret += "."
		ret += self.__class__.__qualname__
		return ret

	def __str__(self) -> str:
		j = self.to_json(indent=2).strip()
		return f"{self.class_path}({j})"

	def __repr__(self) -> str:
		j = self.to_json().strip()
		return f"{self.class_path}({j})"


class SerializableDict(Serializable):
	def to_dict(self) -> dict:
		ret = {}
		for key in dir(self):
			val = getattr(self, key)
			if key.startswith("__"): continue
			if key.endswith("__"): continue
			if callable(val): continue
			ret[key] = val
		return ret

	def from_dict(self, o: dict) -> Self:
		for key in o:
			val = o[key]
			if key.startswith("__"): continue
			if key.endswith("__"): continue
			if callable(val): continue
			setattr(self, key, val)
		return self

	def serialize(self) -> dict:
		return self.to_dict()

	def unserialize(self, value: dict):
		self.from_dict(value)

	def __dict__(self) -> dict:
		return self.to_dict()

	def __init__(self, o: dict = None):
		if o: self.from_dict(o)


class SerializableList(Serializable):
	def to_list(self) -> list:
		pass

	def from_list(self, o: list) -> Self:
		pass

	def serialize(self) -> list:
		return self.to_list()

	def unserialize(self, value: list):
		self.from_list(value)

	def __list__(self) -> list:
		return self.to_list()

	def __init__(self, o: list = None):
		if o: self.from_list(o)
