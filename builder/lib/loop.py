import io
import os
import stat
import fcntl
import ctypes
from builder.lib import utils


LO_NAME_SIZE         = 64
LO_KEY_SIZE          = 32
LO_FLAGS_READ_ONLY   = 1
LO_FLAGS_AUTOCLEAR   = 4
LO_FLAGS_PARTSCAN    = 8
LO_FLAGS_DIRECT_IO   = 16
LO_CRYPT_NONE        = 0
LO_CRYPT_XOR         = 1
LO_CRYPT_DES         = 2
LO_CRYPT_FISH2       = 3
LO_CRYPT_BLOW        = 4
LO_CRYPT_CAST128     = 5
LO_CRYPT_IDEA        = 6
LO_CRYPT_DUMMY       = 9
LO_CRYPT_SKIPJACK    = 10
LO_CRYPT_CRYPTOAPI   = 18
MAX_LO_CRYPT         = 20
LOOP_SET_FD          = 0x4C00
LOOP_CLR_FD          = 0x4C01
LOOP_SET_STATUS      = 0x4C02
LOOP_GET_STATUS      = 0x4C03
LOOP_SET_STATUS64    = 0x4C04
LOOP_GET_STATUS64    = 0x4C05
LOOP_CHANGE_FD       = 0x4C06
LOOP_SET_CAPACITY    = 0x4C07
LOOP_SET_DIRECT_IO   = 0x4C08
LOOP_SET_BLOCK_SIZE  = 0x4C09
LOOP_CONFIGURE       = 0x4C0A
LOOP_CTL_ADD         = 0x4C80
LOOP_CTL_REMOVE      = 0x4C81
LOOP_CTL_GET_FREE    = 0x4C82
LOOP_SET_STATUS_SETTABLE_FLAGS   = LO_FLAGS_AUTOCLEAR | LO_FLAGS_PARTSCAN
LOOP_SET_STATUS_CLEARABLE_FLAGS  = LO_FLAGS_AUTOCLEAR
LOOP_CONFIGURE_SETTABLE_FLAGS    = LO_FLAGS_READ_ONLY | LO_FLAGS_AUTOCLEAR | LO_FLAGS_PARTSCAN | LO_FLAGS_DIRECT_IO


class LoopInfo64(ctypes.Structure):
	_fields_ = [
		("lo_device",            ctypes.c_uint64),
		("lo_inode",             ctypes.c_uint64),
		("lo_rdevice",           ctypes.c_uint64),
		("lo_offset",            ctypes.c_uint64),
		("lo_sizelimit",         ctypes.c_uint64),
		("lo_number",            ctypes.c_uint32),
		("lo_encrypt_type",      ctypes.c_uint32),
		("lo_encrypt_key_size",  ctypes.c_uint32),
		("lo_flags",             ctypes.c_uint32),
		("lo_file_name",         ctypes.c_char * LO_NAME_SIZE),
		("lo_crypt_name",        ctypes.c_char * LO_NAME_SIZE),
		("lo_encrypt_key",       ctypes.c_byte * LO_KEY_SIZE),
		("lo_init",              ctypes.c_uint64 * 2),
	]


class LoopConfig(ctypes.Structure):
	_fields_ = [
		("fd",         ctypes.c_uint32),
		("block_size", ctypes.c_uint32),
		("info",       LoopInfo64),
		("__reserved", ctypes.c_uint64 * 8),
	]


def loop_get_free_no() -> int:
	ctrl = os.open("/dev/loop-control", os.O_RDWR)
	try:
		no = fcntl.ioctl(ctrl, LOOP_CTL_GET_FREE)
		if no < 0: raise OSError("LOOP_CTL_GET_FREE failed")
	finally: os.close(ctrl)
	return no


def loop_get_free() -> str:
	no = loop_get_free_no()
	return f"/dev/loop{no}"


def loop_create_dev(no: int, dev: str = None) -> str:
	if dev is None:
		dev = f"/dev/loop{no}"
	if not os.path.exists(dev):
		if no < 0: raise ValueError("no loop number set")
		a_mode = stat.S_IRUSR | stat.S_IWUSR | stat.S_IFBLK
		a_dev = os.makedev(7, no)
		os.mknod(dev, a_mode, a_dev)
	return dev


def loop_detach(dev: str):
	loop = os.open(dev, os.O_RDWR)
	try:
		ret = fcntl.ioctl(loop, LOOP_CLR_FD)
		if ret != 0: raise OSError(f"detach loop device {dev} failed")
	finally: os.close(loop)


def loop_setup(
	path: str = None,
	fio: io.FileIO = None,
	fd: int = -1,
	dev: str = None,
	no: int = -1,
	offset: int = 0,
	size: int = 0,
	block_size: int = 512,
	read_only: bool = False,
	part_scan: bool = False,
	auto_clear: bool = False,
	direct_io: bool = False,
) -> str:
	if path is None and fio is None and fd < 0:
		raise ValueError("no source file set")
	if no < 0:
		if dev is None:
			dev = loop_get_free()
		else:
			fn = os.path.basename(dev)
			if fn.startswith("loop"): no = int(fn[4:])
	loop_create_dev(no=no, dev=dev)
	opened, loop = -1, -1
	if fio:
		if fd < 0: fd = fio.fileno()
		if path is None: path = fio.name
	elif fd >= 0:
		if path is None: path = utils.fd_get_path(fd)
		if path is None: raise OSError("bad fd for loop")
	elif path:
		path = os.path.realpath(path)
		opened = os.open(path, os.O_RDWR)
		if opened < 0: raise OSError(f"open {path} failed")
		fd = opened
	else: raise ValueError("no source file set")
	flags = 0
	if part_scan: flags |= LO_FLAGS_PARTSCAN
	if direct_io: flags |= LO_FLAGS_DIRECT_IO
	if read_only: flags |= LO_FLAGS_READ_ONLY
	if auto_clear: flags |= LO_FLAGS_AUTOCLEAR
	try:
		file_name = path[0:63].encode()
		li = LoopInfo64(
			lo_flags=flags,
			lo_offset=offset,
			lo_sizelimit=size,
			lo_file_name=file_name,
		)
		lc = LoopConfig(fd=fd, block_size=block_size, info=li)
		loop = os.open(dev, os.O_RDWR)
		if loop < 0: raise OSError(f"open loop device {dev} failed")
		ret = fcntl.ioctl(loop, LOOP_CONFIGURE, lc)
		if ret != 0: raise OSError(f"configure loop device {dev} with {path} failed")
	finally:
		if loop >= 0: os.close(loop)
		if opened >= 0: os.close(opened)
	return dev


def loop_get_sysfs(dev: str) -> str:
	st = os.stat(dev)
	if not stat.S_ISBLK(st.st_mode):
		raise ValueError(f"device {dev} is not block")
	major = os.major(st.st_rdev)
	minor = os.minor(st.st_rdev)
	if major != 7:
		raise ValueError(f"device {dev} is not loop")
	sysfs = f"/sys/dev/block/{major}:{minor}"
	if not os.path.exists(sysfs):
		raise RuntimeError("get sysfs failed")
	return sysfs


def loop_get_backing(dev: str) -> str:
	sysfs = loop_get_sysfs(dev)
	path = os.path.join(sysfs, "loop", "backing_file")
	with open(path, "r") as f:
		backing = f.read()
		return os.path.realpath(backing.strip())


def loop_get_offset(dev: str) -> int:
	sysfs = loop_get_sysfs(dev)
	path = os.path.join(sysfs, "loop", "offset")
	with open(path, "r") as f:
		backing = f.read()
		return int(backing.strip())


class LoopDevice:
	device: str

	def __init__(
		self,
		path: str = None,
		fio: io.FileIO = None,
		fd: int = -1,
		dev: str = None,
		no: int = -1,
		offset: int = 0,
		size: int = 0,
		block_size: int = 512,
		read_only: bool = False,
		part_scan: bool = False,
		auto_clear: bool = False,
		direct_io: bool = False,
	):
		self.device = loop_setup(
			path=path,
			fio=fio,
			fd=fd,
			dev=dev,
			no=no,
			offset=offset,
			size=size,
			block_size=block_size,
			read_only=read_only,
			part_scan=part_scan,
			auto_clear=auto_clear,
			direct_io=direct_io,
		)

	def __del__(self):
		loop_detach(self.device)
