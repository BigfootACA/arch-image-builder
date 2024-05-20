import json
from uuid import UUID
from builder.lib import serializable


class SerializableEncoder(json.JSONEncoder):
	"""
	JSON implement of serializable interface
	"""
	def default(self, o):
		if isinstance(o, UUID):
			return str(o)
		if isinstance(o, serializable.SerializableDict):
			return o.to_dict()
		if isinstance(o, serializable.SerializableList):
			return o.to_list()
		if isinstance(o, serializable.Serializable):
			return o.serialize()
		return super().default(o)


def dump(
	obj, fp, *,
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
):
	if cls is None: cls = SerializableEncoder
	return json.dump(
		obj, fp,
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


def dumps(
	obj, *,
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
):
	if cls is None: cls = SerializableEncoder
	return json.dumps(
		obj,
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


load = json.load
loads = json.loads
