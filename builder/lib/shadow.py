import io
from typing import Self
from builder.lib.serializable import SerializableDict, SerializableList


def zero2empty(num: int) -> str:
	return str(num) if num !=0 else ""


def none2empty(val: str) -> str:
	return val if val else ""


class UserEntry(SerializableDict):
	name: str = None

	def from_line(self, line: str): pass

	def to_line(self) -> str: pass


class UserFile(SerializableList):
	def load_line(self, line: str): pass

	def unload(self): pass

	def load_str(self, content: str | list[str]) -> Self:
		if type(content) is str: 
			content = content.split("\n")
		for line in content:
			line = line.strip()
			if line.startswith("#"): continue
			if len(line) <= 0: continue
			self.load_line(line)
		return self

	def load_fp(self, fp: io.TextIOWrapper) -> Self:
		self.load_str(fp.readlines())
		return self

	def load_file(self, file: str) -> Self:
		with open(file, "r") as f:
			self.load_fp(f)
		return self

	def from_str(self, content: str) -> Self:
		self.unload()
		self.load_str(content)
		return self

	def from_fp(self, fp: io.TextIOWrapper) -> Self:
		self.unload()
		self.load_fp(fp)
		return self

	def from_file(self, file: str) -> Self:
		self.unload()
		self.load_file(file)
		return self


class ShadowEntry(UserEntry):
	name: str = None
	password: str = None
	last_change: int = 0
	min_age: int = 0
	max_age: int = 0
	warning_period: int = 0
	inactivity_period: int = 0
	expiration: int = 0

	def from_line(self, line: str):
		values = line.split(":")
		if len(values) != 8:
			raise ValueError("fields mismatch")
		self.name = values[0]
		self.password = values[1]
		self.last_change = int(values[2]) if len(values[2]) > 0 else 0
		self.min_age = int(values[3]) if len(values[3]) > 0 else 0
		self.max_age = int(values[4]) if len(values[4]) > 0 else 0
		self.warning_period = int(values[5]) if len(values[5]) > 0 else 0
		self.inactivity_period = int(values[6]) if len(values[6]) > 0 else 0
		self.expiration = int(values[7]) if len(values[7]) > 0 else 0

	def to_line(self) -> str:
		values = [
			none2empty(self.name),
			none2empty(self.password),
			zero2empty(self.last_change),
			zero2empty(self.min_age),
			zero2empty(self.max_age),
			zero2empty(self.warning_period),
			zero2empty(self.inactivity_period),
			zero2empty(self.expiration),
		]
		return (":".join(values)) + "\n"


class GshadowEntry(UserEntry):
	name: str = None
	password: str = None
	admins: list[str] = None
	members: list[str] = None

	@property
	def admin(self):
		return ",".join(self.admins)

	@admin.setter
	def admin(self, val: str):
		self.admins = val.split(",")

	@property
	def member(self):
		return ",".join(self.members)

	@member.setter
	def member(self, val: str):
		self.members = val.split(",")

	def from_line(self, line: str):
		values = line.split(":")
		if len(values) != 4:
			raise ValueError("fields mismatch")
		self.name = values[0]
		self.password = values[1]
		self.admin = values[2]
		self.member = values[3]

	def to_line(self) -> str:
		values = [
			none2empty(self.name),
			none2empty(self.password),
			none2empty(self.admin),
			none2empty(self.member),
		]
		return (":".join(values)) + "\n"


class PasswdEntry(UserEntry):
	name: str = None
	password: str = None
	uid: int = -1
	gid: int = -1
	comment: str = None
	home: str = None
	shell: str = None

	def from_line(self, line: str):
		values = line.split(":")
		if len(values) != 7:
			raise ValueError("fields mismatch")
		self.name = values[0]
		self.password = values[1]
		self.uid = int(values[2])
		self.gid = int(values[3])
		self.comment = values[4]
		self.home = values[5]
		self.shell = values[6]

	def to_line(self) -> str:
		values = [
			none2empty(self.name),
			none2empty(self.password),
			str(self.uid),
			str(self.gid),
			none2empty(self.comment),
			none2empty(self.home),
			none2empty(self.shell),
		]
		return (":".join(values)) + "\n"


class GroupEntry(UserEntry):
	name: str = None
	password: str = None
	gid: int = -1
	users: list[str] = None

	@property
	def user(self):
		return ",".join(self.users)

	@user.setter
	def user(self, val: str):
		self.users = val.split(",")

	def from_line(self, line: str):
		values = line.split(":")
		if len(values) != 4:
			raise ValueError("fields mismatch")
		self.name = values[0]
		self.password = values[1]
		self.gid = int(values[2])
		self.user = values[3]

	def to_line(self) -> str:
		values = [
			none2empty(self.name),
			none2empty(self.password),
			str(self.gid),
			none2empty(self.user),
		]
		return (":".join(values)) + "\n"


class ShadowFile(list[ShadowEntry], UserFile):
	def unload(self): self.clear()

	def load_line(self, line: str):
		ent = ShadowEntry()
		ent.from_line(line)
		self.append(ent)
	
	def lookup_name(self, name: str) -> ShadowEntry:
		return next((e for e in self if e.name == name), None)


class GshadowFile(list[GshadowEntry], UserFile):
	def unload(self): self.clear()

	def load_line(self, line: str):
		ent = GshadowEntry()
		ent.from_line(line)
		self.append(ent)
	
	def lookup_name(self, name: str) -> GshadowEntry:
		return next((e for e in self if e.name == name), None)


class PasswdFile(list[PasswdEntry], UserFile):
	def unload(self): self.clear()

	def load_line(self, line: str):
		ent = PasswdEntry()
		ent.from_line(line)
		self.append(ent)
	
	def lookup_name(self, name: str) -> PasswdEntry:
		return next((e for e in self if e.name == name), None)

	def lookup_uid(self, uid: int) -> PasswdEntry:
		return next((e for e in self if e.uid == uid), None)

	def lookup_gid(self, gid: int) -> PasswdEntry:
		return next((e for e in self if e.gid == gid), None)


class GroupFile(list[GroupEntry], UserFile):
	def unload(self): self.clear()

	def load_line(self, line: str):
		ent = GroupEntry()
		ent.from_line(line)
		self.append(ent)
	
	def lookup_name(self, name: str) -> GroupEntry:
		return next((e for e in self if e.name == name), None)

	def lookup_gid(self, gid: int) -> GroupEntry:
		return next((e for e in self if e.gid == gid), None)
