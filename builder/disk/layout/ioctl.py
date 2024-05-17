import ctypes


BLKSSZGET = 0x1268
BLKGETSIZE64 = 0x80081272
HDIO_GETGEO = 0x0301


class HDGeometry(ctypes.Structure):
	_fields_ = [
		("heads",      ctypes.c_ubyte),
		("sectors",    ctypes.c_ubyte),
		("cylinders",  ctypes.c_ushort),
		("start",      ctypes.c_ulong),
	]


assert(ctypes.sizeof(HDGeometry()) == 16)
