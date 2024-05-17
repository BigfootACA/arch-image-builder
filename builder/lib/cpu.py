import os
from logging import getLogger
log = getLogger(__name__)


def cpu_arch_name_map(name: str) -> str:
	"""
	Map cpu arch name to archlinux names
	cpu_arch_name_map("amd64") = "x86_64"
	cpu_arch_name_map("x86_64") = "x86_64"
	cpu_arch_name_map("ARM64") = "arm64"
	"""
	match name.lower():
		case "x64" | "amd64" | "intel64": return "x86_64"
		case "i386" | "i486" | "i586" | "x86" | "ia32": return "i686"
		case "arm64" | "armv8a" | "armv8" | "arm-v8a" | "arm-v8" | "aa64": return "aarch64"
		case "arm32" | "aarch32" | "aa32" | "armv7" | "armv7l" | "arm-v7" | "arm-v7l" | "arm-v7h": return "armv7h"
		case _: return name.lower()


def cpu_arch_get_raw() -> str:
	"""
	Get current cpu arch
	cpu_arch_get() = "amd64"
	cpu_arch_get() = "x86_64"
	cpu_arch_get() = "arm64"
	"""
	return os.uname().machine


def cpu_arch_get() -> str:
	"""
	Get current cpu arch and map to archlinux names
	cpu_arch_get() = "x86_64"
	cpu_arch_get() = "arm64"
	"""
	return cpu_arch_name_map(cpu_arch_get_raw())


def cpu_arch_compatible_one(
	supported: str,
	current: str = cpu_arch_get_raw()
) -> bool:
	"""
	Is current cpu compatible with supported
	cpu_arch_compatible("any", "x86_64") = True
	cpu_arch_compatible("any", "aarch64") = True
	cpu_arch_compatible("aarch64", "x86_64") = False
	cpu_arch_compatible("x86_64", "x86_64") = True
	"""
	cur = cpu_arch_name_map(current.strip())
	name = cpu_arch_name_map(supported.strip())
	if len(name) == 0: return False
	return name == cur or name == "any"


def cpu_arch_compatible(
	supported: str | list[str],
	current: str = cpu_arch_get_raw()
) -> bool:
	"""
	Is current cpu compatible with supported list
	cpu_arch_compatible("any", "x86_64") = True
	cpu_arch_compatible("any", "aarch64") = True
	cpu_arch_compatible("aarch64", "x86_64") = False
	cpu_arch_compatible("x86_64,aarch64", "x86_64") = True
	"""
	if type(supported) is str: arch = supported.split(",")
	elif type(supported) is list: arch = supported
	else: raise TypeError("unknown type for supported")
	for cpu in arch:
		if cpu_arch_compatible_one(cpu, current):
			return True
	return True
