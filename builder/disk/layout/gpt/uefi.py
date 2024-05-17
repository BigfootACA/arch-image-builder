import ctypes
from binascii import crc32
from logging import getLogger
from builder.lib.serializable import Serializable, SerializableDict
from uuid import UUID, uuid4
log = getLogger(__name__)


class EfiTableHeader(ctypes.Structure, SerializableDict):
	_fields_ = [
		("signature",    ctypes.c_uint64),
		("revision",     ctypes.c_uint32),
		("header_size",  ctypes.c_uint32),
		("crc32",        ctypes.c_uint32),
		("reserved",     ctypes.c_uint32),
	]

	def set_signature(self, value: str | int | bytes):
		vt = type(value)
		if vt is str: r = int.from_bytes(value.encode(), "little")
		elif vt is bytes: r = int.from_bytes(value, "little")
		elif vt is int: r = value
		else: raise TypeError("bad value type")
		self.signature = r

	def get_signature(self) -> bytes:
		return ctypes.string_at(ctypes.byref(self), 8)

	def get_revision(self) -> tuple[int, int]:
		return (
			self.revision >> 0x10 & 0xFFFF,
			self.revision & 0xFFFF,
		)

	def calc_crc32(self, data: bytes = None) -> int:
		orig = self.crc32
		self.crc32 = 0
		if data is None: data = ctypes.string_at(
			ctypes.byref(self), self.header_size
		)
		value = crc32(data, 0)
		self.crc32 = orig
		return value

	def update_crc32(self, data: bytes = None):
		self.crc32 = self.calc_crc32(data)

	def check_signature(self, value: str | int | bytes) -> bool:
		vt = type(value)
		if vt is int: return self.signature == value
		b = self.get_signature()
		if vt is bytes: return b == value
		if vt is str: return b == value.encode()
		raise TypeError("bad value type")

	def check_revision(self, major: int, minor: int) -> bool:
		rev = self.get_revision()
		return rev[0] == major and rev[1] == minor

	def check_crc32(self) -> bool:
		return self.calc_crc32() == self.crc32

	def to_dict(self) -> dict:
		return {
			"signature": self.get_signature().decode(),
			"revision": ".".join(map(str, self.get_revision())),
			"header_size": self.header_size,
			"crc32": self.crc32,
		}


class EfiGUID(ctypes.Structure, Serializable):
	_fields_ = [
		("d1", ctypes.c_uint32),
		("d2", ctypes.c_uint16),
		("d3", ctypes.c_uint16),
		("d4", ctypes.c_uint8 * 8),
	]

	def to_uuid(self) -> UUID:
		u = bytes()
		u += int.to_bytes(self.d1, 4)
		u += int.to_bytes(self.d2, 2)
		u += int.to_bytes(self.d3, 2)
		u += bytes().join(int.to_bytes(i) for i in self.d4)
		return UUID(bytes=u)

	def set_uuid(self, u: UUID):
		u = u.bytes
		self.d1 = int.from_bytes(u[0:4])
		self.d2 = int.from_bytes(u[4:6])
		self.d3 = int.from_bytes(u[6:8])
		for i in range(8):
			self.d4[i] = int.from_bytes(u[i+8:i+9])

	@staticmethod
	def from_uuid(u: UUID):
		if u is None: return None
		g = EfiGUID()
		g.set_uuid(u)
		return g

	@staticmethod
	def generate():
		return EfiGUID.from_uuid(uuid4())

	def serialize(self) -> str:
		return str(self.to_uuid())

	def unserialize(self, o: str):
		self.from_uuid(UUID(o))

	def __str__(self) -> str:
		return self.serialize()


assert(ctypes.sizeof(EfiTableHeader()) == 24)
assert(ctypes.sizeof(EfiGUID()) == 16)
