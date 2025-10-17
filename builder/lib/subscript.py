from builder.lib.utils import str_find_all
from logging import getLogger
log = getLogger(__name__)


class SubScriptValue:
	token: str = None
	content: str = None
	original: str = None
	default: str = None
	incomplete: bool = False

	def __str__(self): return self.content
	def __repr__(self): return self.content


def dict_get(key: str, root: dict):
	def get_token(node, k):
		if node is None: return None
		nt = type(node)
		if nt is list: return node.get(int(k), None)
		elif nt is tuple: return node.get(int(k), None)
		elif nt is dict: return node.get(k, None)
		else: raise KeyError(f"unsupported get in {nt.__name__}")
	keys = ["[", "."]
	node = root
	while len(key) > 0:
		if key[0] == "[":
			p = key.find("]", 1)
			if p < 0: raise ValueError("missing ]")
			node = get_token(node, key[1:p])
			key = key[p + 1:]
			continue
		if key[0] == ".":
			key = key[1:]
			continue
		p = str_find_all(key, keys)
		k = key[:p] if p >= 0 else key
		node = get_token(node, k)
		if p < 0: return node
		key = key[p + 1:]
	return node


def resolve_simple_values(original: str, values: dict) -> str:
	value = str(original)
	for key in values:
		value = value.replace(f"${key}", values[key])
	return value


class SubScript:
	root: dict
	resolved: list[str]
	unresolved: list[str]
	count: int

	def resolve_token(self, token: str) -> SubScriptValue:
		val = SubScriptValue()
		val.original = token
		lstr = False
		if token[0] == "@":
			token = token[1:]
			lstr = True
		if ":" in token:
			bval = token.split(":")
			if len(bval) != 2:
				raise ValueError(f"invalid token {token}")
			token = bval[0]
			val.default = bval[1]
		val.token = token
		if token not in self.unresolved:
			self.unresolved.append(token)
		value = dict_get(token, self.root)
		if token not in self.resolved:
			val.incomplete = True
			return val
		if lstr:
			vt = type(value)
			if vt is list: value = " ".join(value)
			else: raise ValueError(f"@ not support for {vt.__name__}")
		self.unresolved.remove(token)
		val.content = value
		return val

	def process(self, content: str, lvl: str, use_def: bool) -> SubScriptValue:
		last = 0
		ret = SubScriptValue()
		ret.original = content
		ret.content = content
		while last < len(content):
			last = content.find("$", last)
			if last < 0: break
			if content[last:last + 2] == "$$":
				content = content[:last] + content[last + 1:]
				last += 1
				continue
			if len(content) <= last + 2 or content[last + 1] != "{":
				raise ValueError(f"unexpected token in subscript at {lvl}")
			tp = content.find("}", last + 1)
			if tp < 0: raise ValueError(f"missing }} in subscript at {lvl}")
			token = content[last + 2: tp]
			val = self.resolve_token(token)
			if val.incomplete:
				if use_def and val.default is not None:
					value = val.default
				else:
					ret.incomplete = True
					return ret
			else:
				value = val.content
			value = str(value)
			content = content[:last] + value + content[tp + 1:]
			last += len(value)
		ret.content = content
		return ret

	def parse_rec(self, node: dict | list, level: str, use_def: bool=False) -> bool:
		def process_one(key, lvl):
			value = node[key]
			vt = type(value)
			if vt is dict or vt is list:
				if not self.parse_rec(value, lvl, use_def):
					return False
			elif vt is str:
				val = self.process(value, lvl, use_def)
				if val.incomplete:
					return False
				node[key] = val.content
			self.resolved.append(lvl)
			self.count += 1
			return True
		ret = True
		nt = type(node)
		if nt is dict:
			for key in node:
				lvl = f"{level}.{key}" if len(level) > 0 else key
				if lvl in self.resolved: continue
				if not process_one(key, lvl): ret = False
		elif nt is list or nt is tuple:
			for idx in range(len(node)):
				lvl = f"{level}[{idx}]"
				if lvl in self.resolved: continue
				if not process_one(idx, lvl): ret = False
		else: raise ValueError(f"unknown input value at {level}")
		return ret

	def dump_unresolved(self):
		for key in self.unresolved:
			log.warning(f"value {key} unresolved")

	def parse(self, root: dict):
		self.root = root
		use_def = False
		while True:
			self.count = 0
			ret = self.parse_rec(root, "", use_def)
			if ret: break
			if self.count > 0:
				continue
			if len(self.unresolved) == 0:
				break
			if not use_def:
				use_def = True
				continue
			self.dump_unresolved()
			raise ValueError("some value cannot be resolved")
		self.dump_unresolved()

	def __init__(self):
		self.resolved = []
		self.unresolved = []
		self.count = 0
