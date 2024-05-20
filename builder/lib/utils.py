import os
import io
import shlex
import shutil
import typing
from logging import getLogger
log = getLogger(__name__)


def str_find_all(
	orig: str,
	keys: list[str] | tuple[str] | str,
	start: typing.SupportsIndex | None = None,
	end: typing.SupportsIndex | None = None,
) -> int:
	"""
	Find the closest string with multiple key
	"""
	if type(keys) is str: return orig.find(keys, start, end)
	result: list[int] = [orig.find(key, start, end) for key in keys]
	while -1 in result: result.remove(-1)
	return min(result, default=-1)


def parse_cmd_args(cmd: str | list[str]) -> list[str]:
	"""
	Parse command line to list
	parse_cmd_args("ls -la /mnt") = ["ls", "-la", "/mnt"]
	parse_cmd_args(["ls", "-la", "/mnt"]) = ["ls", "-la", "/mnt"]
	"""
	if type(cmd) is str: return shlex.split(cmd)
	elif type(cmd) is list: return cmd
	else: raise TypeError("unknown type for cmd")


def find_external(name: str) -> str:
	"""
	Find a linux executable path
	find_external("systemctl") = "/usr/bin/systemctl"
	find_external("service") = None
	"""
	return shutil.which(name)


def have_external(name: str) -> bool:
	"""
	Is a command in PATH
	find_external("systemctl") = True
	find_external("service") = False
	"""
	return shutil.which(name) is not None


def fd_get_path(fd: int) -> str | None:
	"""
	Get file path by FD
	fd_get_path(1) = "/dev/pts/0"
	"""
	link = f"/proc/self/fd/{fd}"

	# target is not exists?
	if not os.path.exists(link): return None

	# read link of fd
	path = os.readlink(link)

	# must starts with / (is an absolute path)
	if not path.startswith("/"): return None

	# do not use memfd
	if path.startswith("/memfd:"): return None

	# do not use a deleted file
	if path.endswith(" (deleted)"): return None

	# target file is not exists (should not happen)
	if not os.path.exists(path): return None

	return path


def size_to_bytes(value: str | int, alt_units: dict = None) -> int:
	"""
	Convert human-readable size string to number
	size_to_bytes("1MiB") = 1048576
	size_to_bytes("4K") = 4096
	size_to_bytes("64b") = 8
	size_to_bytes(123) = 123
	size_to_bytes("2048s", {'s': 512}) = 1048576
	"""
	units = {
		'b': 0.125, 'bit': 0.125, 'bits': 0.125, 'Bit': 0.125, 'Bits': 0.125,
		'B': 1, 'Byte': 1, 'Bytes': 1, 'bytes': 1, 'byte': 1,
		'k': 10**3, 'kB': 10**3, 'kb': 10**3, 'K': 2**10, 'KB': 2**10, 'KiB': 2**10,
		'm': 10**6, 'mB': 10**6, 'mb': 10**6, 'M': 2**20, 'MB': 2**20, 'MiB': 2**20,
		'g': 10**9, 'gB': 10**9, 'gb': 10**9, 'G': 2**30, 'GB': 2**30, 'GiB': 2**30,
		't': 10**12, 'tB': 10**12, 'tb': 10**12, 'T': 2**40, 'TB': 2**40, 'TiB': 2**40,
		'p': 10**15, 'pB': 10**15, 'pb': 10**15, 'P': 2**50, 'PB': 2**50, 'PiB': 2**50,
		'e': 10**15, 'eB': 10**15, 'eb': 10**15, 'E': 2**50, 'EB': 2**50, 'EiB': 2**50,
		'z': 10**15, 'zB': 10**15, 'zb': 10**15, 'Z': 2**50, 'ZB': 2**50, 'ZiB': 2**50,
		'y': 10**15, 'yB': 10**15, 'yb': 10**15, 'Y': 2**50, 'YB': 2**50, 'YiB': 2**50,
	}
	if type(value) is int:
		# return number directly
		return value
	elif type(value) is str:
		# add custom units
		if alt_units: units.update(alt_units)

		# find all matched units
		matches = {unit: len(unit) for unit in units if value.endswith(unit)}

		# find out the longest matched unit
		max_unit = max(matches.values(), default=0)

		# use the longest unit
		unit = next((unit for unit in matches.keys() if matches[unit] == max_unit), None)

		# get mul for target unit
		mul = units[unit] if unit else 1.0

		# convert string to target number
		return int(float(value[:len(value)-max_unit].strip()) * mul)
	else: raise TypeError("bad size value")


def bytes_pad(b: bytes, size: int, trunc: bool = False, pad: bytes = b'\0') -> bytes:
	"""
	Padding a bytes to specified length
	"""
	l = len(b)

	# if larger than specified size, truncate
	if l > size and trunc:
		b = b[:size]

	# if smaller than specified size, padding
	if l < size:
		b += pad * (size - l)
	return b


def round_up(value: int, align: int) -> int:
	"""
	Align up a number
	round_down(0x2000, 0x1000) = 0x2000
	round_down(0x2001, 0x1000) = 0x3000
	round_down(0x1FFF, 0x1000) = 0x2000
	"""
	return (value + align - 1) & ~(align - 1)


def round_down(value: int, align: int) -> int:
	"""
	Align down a number
	round_down(0x2000, 0x1000) = 0x2000
	round_down(0x2001, 0x1000) = 0x2000
	round_down(0x1FFF, 0x1000) = 0x1000
	"""
	return value & ~(align - 1)


def open_config(path: str, mode=0o0644) -> io.TextIOWrapper:
	"""
	Open a config file for write
	If original file is existing, move to FILE.dist
	"""
	dist = f"{path}.dist"
	have_dist = False
	if os.path.exists(dist):
		# dist file already exists, no move
		have_dist = True
	elif os.path.exists(path):
		# target file already exists, rename to dist
		shutil.move(path, dist)
		have_dist = True
	# FIXME: should not move previous write to dist

	# open and truncate
	flags = os.O_RDWR | os.O_CREAT | os.O_TRUNC
	fd = os.open(path=path, flags=flags, mode=mode)
	if fd < 0: raise IOError(f"open {path} failed")
	try:
		fp = os.fdopen(fd, "w")
		# write a comment to tell user dist was renamed
		fp.write("# This file is auto generated by arch-image-builder\n")
		if have_dist:
			fn = os.path.basename(dist)
			fp.write(f"# Original file is {fn}\n")
		fp.write("\n")
		fp.flush()
	except:
		os.close(fd)
		raise
	# file close managed by parent function
	return fp


def path_to_name(path: str) -> str:
	"""
	Convert path to a identifier
	path_to_name("") = "empty"
	path_to_name("/") = "rootfs"
	path_to_name("/boot") = "boot"
	path_to_name("/etc/fstab") = "etc-fstab"
	"""
	if path == "/": return "rootfs"
	if path.startswith("/"): path = path[1:]
	if len(path) <= 0: return "empty"
	return path.replace("/", "-")
