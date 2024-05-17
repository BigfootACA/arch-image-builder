from ctypes import *


class BlkidType:
	blkid = None
	ptr = POINTER(c_uint64)

	@property
	def pptr(self): return pointer(self.ptr)

	def __init__(self, blkid, ptr: c_void_p=None):
		self.blkid = blkid
		if ptr: self.ptr = ptr


class BlkidCache(BlkidType): pass
class BlkidProbe(BlkidType): pass
class BlkidDevice(BlkidType): pass
class BlkidDeviceIterate(BlkidType): pass
class BlkidTagIterate(BlkidType): pass
class BlkidTopology(BlkidType): pass
class BlkidPartList(BlkidType): pass
class BlkidPartTable(BlkidType): pass
class BlkidPartition(BlkidType): pass


class Blkid:
	obj: CDLL=None
	BLKID_DEV_FIND   = 0x0000
	BLKID_DEV_CREATE = 0x0001
	BLKID_DEV_VERIFY = 0x0002
	BLKID_DEV_NORMAL = 0x0003
	BLKID_SUBLKS_LABEL    = (1 << 1)
	BLKID_SUBLKS_LABELRAW = (1 << 2)
	BLKID_SUBLKS_UUID     = (1 << 3)
	BLKID_SUBLKS_UUIDRAW  = (1 << 4)
	BLKID_SUBLKS_TYPE     = (1 << 5)
	BLKID_SUBLKS_SECTYPE  = (1 << 6)
	BLKID_SUBLKS_USAGE    = (1 << 7)
	BLKID_SUBLKS_VERSION  = (1 << 8)
	BLKID_SUBLKS_MAGIC    = (1 << 9)
	BLKID_SUBLKS_BADCSUM  = (1 << 10)
	BLKID_SUBLKS_FSINFO   = (1 << 11)
	BLKID_SUBLKS_DEFAULT  = ((1 << 1) | (1 << 3) | (1 << 5) | (1 << 6))
	BLKID_FLTR_NOTIN  = 1
	BLKID_FLTR_ONLYIN = 2
	BLKID_USAGE_FILESYSTEM = (1 << 1)
	BLKID_USAGE_RAID       = (1 << 2)
	BLKID_USAGE_CRYPTO     = (1 << 3)
	BLKID_USAGE_OTHER      = (1 << 4)
	BLKID_PARTS_FORCE_GPT     = (1 << 1)
	BLKID_PARTS_ENTRY_DETAILS = (1 << 2)
	BLKID_PARTS_MAGIC         = (1 << 3)
	BLKID_PROBE_OK        = 0
	BLKID_PROBE_NONE      = 1
	BLKID_PROBE_ERROR     = -1
	BLKID_PROBE_AMBIGUOUS = -2

	def __init__(self):
		self.obj = CDLL("libblkid.so.1")

	def init_debug(self, mask: int) -> None:
		self.obj.blkid_init_debug.argtypes = (c_int, )
		self.obj.blkid_init_debug(mask)

	def put_cache(self, cache: BlkidCache) -> None:
		self.obj.blkid_put_cache(cache.ptr)

	def get_cache(self, filename: str=None) -> tuple[int, BlkidCache]:
		cache = BlkidCache(self)
		self.obj.blkid_get_cache.argtypes = (c_void_p, c_char_p, )
		self.obj.blkid_get_cache.restype = c_int
		c = cache.ptr if cache else None
		f = filename.encode() if filename else None
		ret = self.obj.blkid_get_cache(c, f)
		return (ret, cache)

	def gc_cache(self, cache: BlkidCache) -> None:
		self.obj.blkid_gc_cache.argtypes = (c_void_p, )
		self.obj.blkid_gc_cache(cache.ptr)

	def dev_devname(self, dev: BlkidDevice) -> str:
		self.obj.blkid_dev_devname.argtypes = (c_void_p, )
		self.obj.blkid_dev_devname.restype = c_char_p
		ret = self.obj.blkid_dev_devname(dev.ptr)
		return ret.decode() if ret else None

	def dev_iterate_begin(self, cache: BlkidCache) -> BlkidDeviceIterate:
		iter = BlkidDeviceIterate(self)
		self.obj.blkid_dev_iterate_begin.argtypes = (c_void_p, )
		self.obj.blkid_dev_iterate_begin.restype = c_void_p
		iter.ptr = self.obj.blkid_dev_iterate_begin(cache.ptr)
		return iter

	def dev_set_search(self, iter: BlkidDeviceIterate, type: str=None, value: str=None) -> int:
		self.obj.blkid_dev_set_search.argtypes = (c_void_p, c_char_p, c_char_p, )
		self.obj.blkid_dev_set_search.restype = c_int
		return self.obj.blkid_dev_set_search(iter, type, value)

	def dev_next(self, iter: BlkidDeviceIterate) -> tuple[int, BlkidDevice]:
		dev = BlkidDevice(self)
		self.obj.blkid_dev_next.argtypes = (c_void_p, c_void_p, )
		self.obj.blkid_dev_next.restype = c_int
		ret = self.obj.blkid_dev_next(iter.ptr, dev.pptr)
		return (ret, dev)

	def dev_iterate_end(self, iter: BlkidDeviceIterate):
		self.obj.blkid_dev_iterate_end.argtypes = (c_void_p, )
		self.obj.blkid_dev_iterate_end(iter.ptr)

	def devno_to_devname(self, devno: int) -> str:
		self.obj.blkid_devno_to_devname.argtypes = (c_int, )
		self.obj.blkid_devno_to_devname.restype = c_char_p
		ret = self.obj.blkid_devno_to_devname(devno)
		return ret.decode() if ret else None

	def devno_to_wholedisk(self, dev: int, diskname: str, len: int) -> tuple[int, int]:
		diskdevno = c_uint64(0)
		ptr = pointer(diskdevno)
		self.obj.blkid_devno_to_wholedisk.argtypes = (c_int, c_char_p, POINTER(c_int), )
		self.obj.blkid_devno_to_wholedisk.restype = c_int
		d = diskname.encode() if diskname else None
		ret = self.obj.blkid_devno_to_wholedisk(dev, d, len, ptr)
		return (ret, diskdevno)

	def probe_all(self, cache: BlkidCache) -> int:
		self.obj.blkid_probe_all.argtypes = (c_void_p, )
		self.obj.blkid_probe_all.restype = c_int
		return self.obj.blkid_probe_all(cache.ptr)

	def probe_all_new(self, cache: BlkidCache) -> int:
		self.obj.blkid_probe_all_new.argtypes = (c_void_p, )
		self.obj.blkid_probe_all_new.restype = c_int
		return self.obj.blkid_probe_all_new(cache.ptr)

	def probe_all_removable(self, cache: BlkidCache) -> int:
		self.obj.blkid_probe_all_removable.argtypes = (c_void_p, )
		self.obj.blkid_probe_all_removable.restype = c_int
		return self.obj.blkid_probe_all_removable(cache.ptr)

	def get_dev(self, cache: BlkidCache, devname: str, flags: int) -> BlkidDevice:
		dev = BlkidDevice(self)
		self.obj.blkid_get_dev.argtypes = (c_void_p, c_char_p, c_int, )
		self.obj.blkid_get_dev.restype = c_void_p
		dev.ptr = self.obj.blkid_get_dev(cache.ptr, devname, flags)
		return dev

	def get_dev_size(self, fd: int):
		self.obj.blkid_get_dev_size.argtypes = (c_int, )
		self.obj.blkid_get_dev_size.restype = c_uint64
		return self.obj.blkid_get_dev_size(fd)

	def verify(self, cache: BlkidCache, dev: BlkidDevice) -> BlkidDevice:
		ret = BlkidDevice(self)
		self.obj.blkid_verify.argtypes = (c_void_p, c_void_p, )
		self.obj.blkid_verify.restype = c_void_p
		ret.ptr = self.obj.blkid_verify(cache.ptr, dev.ptr)
		return ret

	def get_tag_value(self, iter: BlkidDeviceIterate=None, tagname: str=None, devname: str=None) -> str:
		self.obj.blkid_get_tag_value.argtypes = (c_void_p, c_char_p, c_char_p, )
		self.obj.blkid_get_tag_value.restype = c_char_p
		i = iter.ptr if iter else None
		t = tagname.encode() if tagname else None
		d = devname.encode() if devname else None
		ret = self.obj.blkid_get_tag_value(i, t, d)
		return ret.decode() if ret else None

	def get_devname(self, iter: BlkidDeviceIterate=None, token: str=None, value: str=None) -> str:
		self.obj.blkid_get_devname.argtypes = (c_void_p, c_char_p, c_char_p, )
		self.obj.blkid_get_devname.restype = c_char_p
		i = iter.ptr if iter else None
		t = token.encode() if token else None
		v = value.encode() if value else None
		ret = self.obj.blkid_get_devname(i, t, v)
		return ret.decode() if ret else None

	def tag_iterate_begin(self, dev: BlkidDevice) -> BlkidTagIterate:
		ret = BlkidTagIterate(self)
		self.obj.blkid_tag_iterate_begin.argtypes = (c_void_p, )
		self.obj.blkid_tag_iterate_begin.restype = c_void_p
		ret.ptr = self.obj.blkid_tag_iterate_begin(dev.ptr)
		return ret

	def tag_next(self, iter: BlkidTagIterate) -> tuple[int, str, str]:
		type = POINTER(c_char_p)
		value = POINTER(c_char_p)
		self.obj.blkid_tag_next.argtypes = (c_void_p, c_void_p, c_void_p, )
		self.obj.blkid_tag_next.restype = c_int
		ret = self.obj.blkid_tag_next(iter.ptr, type, value)
		return (ret, type, value)

	def tag_iterate_end(self, iter: BlkidTagIterate):
		self.obj.blkid_tag_iterate_end.argtypes = (c_void_p, )
		self.obj.blkid_tag_iterate_end(iter.ptr)


	def dev_has_tag(self, dev: BlkidDevice, type: str=None, value: str=None) -> int:
		self.obj.blkid_dev_has_tag.argtypes = (c_void_p, str, str)
		self.obj.blkid_dev_has_tag.restype = c_int
		return self.obj.blkid_dev_has_tag(dev.ptr, type, value)

	def find_dev_with_tag(self, cache: BlkidCache, type: str=None, value: str=None) -> BlkidDevice:
		self.obj.blkid_find_dev_with_tag.argtypes = (c_void_p, str, str)
		self.obj.blkid_find_dev_with_tag.restype = c_void_p
		dev = BlkidDevice(self)
		dev.ptr = self.obj.blkid_find_dev_with_tag(cache.ptr, type, value)
		return dev

	def parse_tag_string(self, token: str) -> tuple[int, str, str]:
		self.obj.blkid_parse_tag_string.argtypes = (c_char_p, c_void_p, c_void_p, )
		self.obj.blkid_parse_tag_string.restype = c_int
		type = POINTER(c_char_p)
		value = POINTER(c_char_p)
		ret = self.obj.blkid_parse_tag_string(token, type, value)
		return (ret, type, value)

	def parse_version_string(self, ver_string: str) -> int:
		self.obj.blkid_parse_version_string.argtypes = (c_char_p, )
		self.obj.blkid_parse_version_string.restype = c_int
		return self.obj.blkid_parse_version_string(ver_string)

	def get_library_version(self) -> tuple[int, str, str]:
		self.obj.blkid_get_library_version.argtypes = (c_char_p, c_char_p, )
		self.obj.blkid_get_library_version.restype = c_int
		ver = POINTER(c_char_p)
		date = POINTER(c_char_p)
		ret = self.obj.blkid_get_library_version(ver, date)
		return (ret, ver, date)

	def encode_string(self, str: str, str_enc: str, len: int) -> int:
		self.obj.blkid_encode_string.argtypes = (c_char_p, c_char_p, c_uint64, )
		self.obj.blkid_encode_string.restype = c_int
		return self.obj.blkid_encode_string(str, str_enc, len)

	def safe_string(self, str: str, str_safe: str, len: int) -> int:
		self.obj.blkid_safe_string.argtypes = (c_char_p, c_char_p, c_uint64, )
		self.obj.blkid_safe_string.restype = c_int
		return self.obj.blkid_safe_string(str, str_safe, len)

	def send_uevent(self, devname: str, action: str) -> int:
		self.obj.blkid_send_uevent.argtypes = (c_char_p, c_char_p, )
		self.obj.blkid_send_uevent.restype = c_int
		return self.obj.blkid_send_uevent(devname, action)

	def evaluate_tag(self, token: str, value: str=None, cache: BlkidCache=None) -> str:
		self.obj.blkid_evaluate_tag.argtypes = (c_char_p, c_char_p, c_void_p, )
		self.obj.blkid_evaluate_tag.restype = c_char_p
		t = token.encode() if token else None
		v = value.encode() if value else None
		c = cache.pptr if cache else None
		ret = self.obj.blkid_evaluate_tag(t, v, c)
		return ret.decode() if ret else None

	def evaluate_spec(self, spec: str, cache: BlkidCache) -> str:
		self.obj.blkid_evaluate_tag.argtypes = (c_char_p, c_void_p, )
		self.obj.blkid_evaluate_tag.restype = c_char_p
		s = spec.encode() if spec else None
		c = cache.pptr if cache else None
		ret = self.obj.blkid_evaluate_spec(s, c)
		return ret.decode() if ret else None

	def new_probe(self) -> BlkidProbe:
		self.obj.blkid_new_probe.argtypes = ()
		self.obj.blkid_new_probe.restype = c_void_p
		return BlkidProbe(self, self.obj.blkid_new_probe())

	def new_probe_from_filename(self, filename: str) -> BlkidProbe:
		self.obj.blkid_new_probe_from_filename.argtypes = (c_char_p, )
		self.obj.blkid_new_probe_from_filename.restype = c_void_p
		return BlkidProbe(self, self.obj.blkid_new_probe_from_filename(filename))

	def free_probe(self, pr: BlkidProbe):
		self.obj.blkid_free_probe.argtypes = (c_void_p, )
		self.obj.blkid_free_probe.restype = None
		self.obj.blkid_free_probe(pr.ptr)

	def reset_probe(self, pr: BlkidProbe):
		self.obj.blkid_reset_probe.argtypes = (c_void_p, )
		self.obj.blkid_reset_probe.restype = None
		self.obj.blkid_reset_probe(pr.ptr)

	def probe_reset_buffers(self, pr: BlkidProbe) -> int:
		self.obj.blkid_probe_reset_buffers.argtypes = (c_void_p, )
		self.obj.blkid_probe_reset_buffers.restype = c_int
		return self.obj.blkid_probe_reset_buffers(pr.ptr)

	def probe_hide_range(self, pr: BlkidProbe, off: int, len: int) -> int:
		self.obj.blkid_probe_hide_range.argtypes = (c_void_p, c_uint64, c_uint64, )
		self.obj.blkid_probe_hide_range.restype = c_int
		return self.obj.blkid_probe_hide_range(pr.ptr, off, len)

	def probe_set_device(self, pr: BlkidProbe, fd: int, off: int, size: int) -> int:
		self.obj.blkid_probe_set_device.argtypes = (c_void_p, c_int, c_uint64, c_uint64, )
		self.obj.blkid_probe_set_device.restype = c_int
		return self.obj.blkid_probe_set_device(pr.ptr, fd, off, size)

	def probe_get_devno(self, pr: BlkidProbe) -> int:
		self.obj.blkid_probe_get_devno.argtypes = (c_void_p, )
		self.obj.blkid_probe_get_devno.restype = c_uint64
		return self.obj.blkid_probe_get_devno()

	def probe_get_wholedisk_devno(self, pr: BlkidProbe) -> int:
		self.obj.blkid_probe_get_wholedisk_devno.argtypes = (c_void_p, )
		self.obj.blkid_probe_get_wholedisk_devno.restype = c_uint64
		return self.obj.blkid_probe_get_wholedisk_devno()

	def probe_is_wholedisk(self, pr: BlkidProbe) -> int:
		self.obj.blkid_probe_is_wholedisk.argtypes = (c_void_p, )
		self.obj.blkid_probe_is_wholedisk.restype = c_int
		return self.obj.blkid_probe_is_wholedisk(pr.ptr)

	def probe_get_size(self, pr: BlkidProbe) -> int:
		self.obj.blkid_probe_get_size.argtypes = (c_void_p, )
		self.obj.blkid_probe_get_size.restype = c_uint64
		return self.obj.blkid_probe_get_size(pr.ptr)

	def probe_get_offset(self, pr: BlkidProbe) -> int:
		self.obj.blkid_probe_get_offset.argtypes = (c_void_p, )
		self.obj.blkid_probe_get_offset.restype = c_uint64
		return self.obj.blkid_probe_get_offset(pr.ptr)

	def probe_get_sectorsize(self, pr: BlkidProbe) -> int:
		self.obj.blkid_probe_get_sectorsize.argtypes = (c_void_p, )
		self.obj.blkid_probe_get_sectorsize.restype = c_uint
		return self.obj.blkid_probe_get_sectorsize(pr.ptr)

	def probe_set_sectorsize(self, pr: BlkidProbe, sz: int) -> int:
		self.obj.blkid_probe_set_sectorsize.argtypes = (c_void_p, c_uint, )
		self.obj.blkid_probe_set_sectorsize.restype = c_int
		return self.obj.blkid_probe_set_sectorsize(pr.ptr, sz)

	def probe_get_sectors(self, pr: BlkidProbe) -> int:
		self.obj.blkid_probe_get_sectors.argtypes = (c_void_p, )
		self.obj.blkid_probe_get_sectors.restype = c_uint64
		return self.obj.blkid_probe_get_sectors(pr.ptr)

	def probe_get_fd(self, pr: BlkidProbe) -> int:
		self.obj.blkid_probe_get_fd.argtypes = (c_void_p, )
		self.obj.blkid_probe_get_fd.restype = c_int
		return self.obj.blkid_probe_get_fd(pr.ptr)

	def probe_set_hint(self, pr: BlkidProbe, name: str, value: int) -> int:
		self.obj.blkid_probe_set_hint.argtypes = (c_void_p, c_char_p, c_uint64, )
		self.obj.blkid_probe_set_hint.restype = c_int
		return self.obj.blkid_probe_set_hint(pr.ptr, name, value)

	def probe_reset_hints(self, pr: BlkidProbe):
		self.obj.blkid_probe_reset_hints.argtypes = (c_void_p, )
		self.obj.blkid_probe_reset_hints.restype = None
		self.obj.blkid_probe_reset_hints(pr.ptr)

	def known_fstype(self, fstype: str) -> int:
		self.obj.blkid_known_fstype.argtypes = (c_char_p, )
		self.obj.blkid_known_fstype.restype = c_int
		return self.obj.blkid_known_fstype(fstype)

	def superblocks_get_name(self, idx: int, name: str, usage: int) -> int:
		self.obj.blkid_superblocks_get_name.argtypes = (c_uint64, c_void_p, c_void_p, )
		self.obj.blkid_superblocks_get_name.restype = c_int
		name = POINTER(c_char_p)
		usage = POINTER(c_int)
		return self.obj.blkid_superblocks_get_name(idx, name, usage)

	def probe_enable_superblocks(self, pr: BlkidProbe, enable: bool) -> int:
		self.obj.blkid_probe_enable_superblocks.argtypes = (c_void_p, c_int, )
		self.obj.blkid_probe_enable_superblocks.restype = c_int
		return self.obj.blkid_probe_enable_superblocks(pr.ptr, enable)

	def probe_set_superblocks_flags(self, pr: BlkidProbe, flags: int) -> int:
		self.obj.blkid_probe_set_superblocks_flags.argtypes = (c_void_p, c_int, )
		self.obj.blkid_probe_set_superblocks_flags.restype = c_int
		return self.obj.blkid_probe_set_superblocks_flags(pr.ptr, flags)

	def probe_reset_superblocks_filter(self, pr: BlkidProbe) -> int:
		self.obj.blkid_probe_reset_superblocks_filter.argtypes = (c_void_p, )
		self.obj.blkid_probe_reset_superblocks_filter.restype = c_int
		return self.obj.blkid_probe_reset_superblocks_filter(pr.ptr)

	def probe_invert_superblocks_filter(self, pr: BlkidProbe) -> int:
		self.obj.blkid_probe_invert_superblocks_filter.argtypes = (c_void_p, )
		self.obj.blkid_probe_invert_superblocks_filter.restype = c_int
		return self.obj.blkid_probe_invert_superblocks_filter(pr.ptr)

	def probe_filter_superblocks_type(self, pr: BlkidProbe, flag: int, names: list[str]) -> int:
		self.obj.blkid_probe_filter_superblocks_type.argtypes = (c_void_p, c_int, c_void_p)
		self.obj.blkid_probe_filter_superblocks_type.restype = c_int
		return self.obj.blkid_probe_filter_superblocks_type(pr.ptr, flag, names)

	def probe_filter_superblocks_usage(self, pr: BlkidProbe, flag: int, usage: int) -> int:
		self.obj.blkid_probe_filter_superblocks_usage.argtypes = (c_void_p, c_int, c_int, )
		self.obj.blkid_probe_filter_superblocks_usage.restype = c_int
		return self.obj.blkid_probe_filter_superblocks_usage(pr.ptr, flag, usage)

	def probe_enable_topology(self, pr: BlkidProbe, enable: bool) -> int:
		self.obj.blkid_probe_enable_topology.argtypes = (c_void_p, c_int, )
		self.obj.blkid_probe_enable_topology.restype = c_int
		return self.obj.blkid_probe_enable_topology(pr.ptr, enable)

	def probe_get_topology(self, pr: BlkidProbe) -> BlkidTopology:
		self.obj.blkid_probe_get_topology.argtypes = (c_void_p, )
		self.obj.blkid_probe_get_topology.restype = c_void_p
		return BlkidTopology(self, self.obj.blkid_probe_get_topology(pr.ptr))

	def topology_get_alignment_offset(self, tp: BlkidTopology) -> int:
		self.obj.blkid_topology_get_alignment_offset.argtypes = (c_void_p, )
		self.obj.blkid_topology_get_alignment_offset.restype = c_ulong
		return self.obj.blkid_topology_get_alignment_offset(tp.ptr)

	def topology_get_minimum_io_size(self, tp: BlkidTopology) -> int:
		self.obj.blkid_topology_get_minimum_io_size.argtypes = (c_void_p, )
		self.obj.blkid_topology_get_minimum_io_size.restype = c_ulong
		return self.obj.blkid_topology_get_minimum_io_size(tp.ptr)

	def topology_get_optimal_io_size(self, tp: BlkidTopology) -> int:
		self.obj.blkid_topology_get_optimal_io_size.argtypes = (c_void_p, )
		self.obj.blkid_topology_get_optimal_io_size.restype = c_ulong
		return self.obj.blkid_topology_get_optimal_io_size(tp.ptr)

	def topology_get_logical_sector_size(self, tp: BlkidTopology) -> int:
		self.obj.blkid_topology_get_logical_sector_size.argtypes = (c_void_p, )
		self.obj.blkid_topology_get_logical_sector_size.restype = c_ulong
		return self.obj.blkid_topology_get_logical_sector_size(tp.ptr)

	def topology_get_physical_sector_size(self, tp: BlkidTopology) -> int:
		self.obj.blkid_topology_get_physical_sector_size.argtypes = (c_void_p, )
		self.obj.blkid_topology_get_physical_sector_size.restype = c_ulong
		return self.obj.blkid_topology_get_physical_sector_size(tp.ptr)

	def topology_get_dax(self, tp: BlkidTopology) -> int:
		self.obj.blkid_topology_get_dax.argtypes = (c_void_p, )
		self.obj.blkid_topology_get_dax.restype = c_ulong
		return self.obj.blkid_topology_get_dax(tp.ptr)

	def topology_get_diskseq(self, tp: BlkidTopology) -> int:
		self.obj.blkid_topology_get_diskseq.argtypes = (c_void_p, )
		self.obj.blkid_topology_get_diskseq.restype = c_uint64
		return self.obj.blkid_topology_get_diskseq(tp.ptr)

	def known_pttype(self, pttype: str) -> int:
		self.obj.blkid_known_pttype.argtypes = (c_char_p, )
		self.obj.blkid_known_pttype.restype = c_int
		return self.obj.blkid_known_pttype(pttype)

	def partitions_get_name(self, idx: int, name: str) -> tuple[int, str]:
		self.obj.blkid_partitions_get_name.argtypes = (c_uint64, c_void_p, )
		self.obj.blkid_partitions_get_name.restype = c_int
		tname = c_char_p(name.encode())
		pname = pointer(tname)
		ret = self.obj.blkid_partitions_get_name(idx, pname)
		return (ret, tname.decode())

	def probe_enable_partitions(self, pr: BlkidProbe, enable: c_bool) -> int:
		self.obj.blkid_probe_enable_partitions.argtypes = (c_void_p, c_int, )
		self.obj.blkid_probe_enable_partitions.restype = c_int
		return self.obj.blkid_probe_enable_partitions(pr.ptr, enable)

	def probe_reset_partitions_filter(self, pr: BlkidProbe) -> int:
		self.obj.blkid_probe_reset_partitions_filter.argtypes = (c_void_p, )
		self.obj.blkid_probe_reset_partitions_filter.restype = c_int
		return self.obj.blkid_probe_reset_partitions_filter(pr.ptr)

	def probe_invert_partitions_filter(self, pr: BlkidProbe) -> int:
		self.obj.blkid_probe_invert_partitions_filter.argtypes = (c_void_p, )
		self.obj.blkid_probe_invert_partitions_filter.restype = c_int
		return self.obj.blkid_probe_invert_partitions_filter(pr.ptr)

	def probe_filter_partitions_type(self, pr: BlkidProbe, flag: int, names: list[str]) -> int:
		self.obj.blkid_probe_filter_partitions_type.argtypes = (c_void_p, c_int, c_void_p, )
		self.obj.blkid_probe_filter_partitions_type.restype = c_int
		return self.obj.blkid_probe_filter_partitions_type(pr.ptr, flag, names)

	def probe_set_partitions_flags(self, pr: BlkidProbe, flags: int) -> int:
		self.obj.blkid_probe_set_partitions_flags.argtypes = (c_void_p, c_int, )
		self.obj.blkid_probe_set_partitions_flags.restype = c_int
		return self.obj.blkid_probe_set_partitions_flags(pr.ptr, flags)

	def probe_get_partitions(self, pr: BlkidProbe) -> BlkidPartList:
		self.obj.blkid_probe_get_partitions.argtypes = (c_void_p, )
		self.obj.blkid_probe_get_partitions.restype = c_void_p
		return BlkidPartList(self, self.obj.blkid_probe_get_partitions(pr.ptr))

	def partlist_numof_partitions(self, ls: BlkidPartList) -> int:
		self.obj.blkid_partlist_numof_partitions.argtypes = (c_void_p, )
		self.obj.blkid_partlist_numof_partitions.restype = c_int
		return self.obj.blkid_partlist_numof_partitions(ls.ptr)

	def partlist_get_table(self, ls: BlkidPartList) -> BlkidPartTable:
		self.obj.blkid_partlist_get_table.argtypes = (c_void_p, )
		self.obj.blkid_partlist_get_table.restype = c_void_p
		return BlkidPartTable(self, self.obj.blkid_partlist_get_table(ls.ptr))

	def partlist_get_partition(self, ls: BlkidPartList, n: int) -> BlkidPartition:
		self.obj.blkid_partlist_get_partition.argtypes = (c_void_p, c_int, )
		self.obj.blkid_partlist_get_partition.restype = c_void_p
		return BlkidPartition(self, self.obj.blkid_partlist_get_partition(ls.ptr, n))

	def partlist_get_partition_by_partno(self, ls: BlkidPartList, n: int) -> BlkidPartition:
		self.obj.blkid_partlist_get_partition_by_partno.argtypes = (c_void_p, c_int, )
		self.obj.blkid_partlist_get_partition_by_partno.restype = c_void_p
		return BlkidPartition(self, self.obj.blkid_partlist_get_partition_by_partno(ls.ptr, n))

	def partlist_devno_to_partition(self, ls: BlkidPartList, devno: int) -> BlkidPartition:
		self.obj.blkid_partlist_devno_to_partition.argtypes = (c_void_p, c_int, )
		self.obj.blkid_partlist_devno_to_partition.restype = c_void_p
		return BlkidPartition(self, self.obj.blkid_partlist_devno_to_partition(ls.ptr, devno))

	def partition_get_table(self, par: BlkidPartition) -> BlkidPartTable:
		self.obj.blkid_partition_get_table.argtypes = (c_void_p, )
		self.obj.blkid_partition_get_table.restype = c_void_p
		return BlkidPartTable(self, self.obj.blkid_partition_get_table(par.ptr))

	def partition_get_name(self, par: BlkidPartition) -> str:
		self.obj.blkid_partition_get_name.argtypes = (c_void_p, )
		self.obj.blkid_partition_get_name.restype = c_char_p
		return self.obj.blkid_partition_get_name(par.ptr).decode()

	def partition_get_uuid(self, par: BlkidPartition) -> str:
		self.obj.blkid_partition_get_uuid.argtypes = (c_void_p, )
		self.obj.blkid_partition_get_uuid.restype = c_char_p
		return self.obj.blkid_partition_get_uuid(par.ptr).decode()

	def partition_get_partno(self, par: BlkidPartition) -> int:
		self.obj.blkid_partition_get_partno.argtypes = (c_void_p, )
		self.obj.blkid_partition_get_partno.restype = c_int
		return self.obj.blkid_partition_get_partno(par.ptr)

	def partition_get_start(self, par: BlkidPartition) -> int:
		self.obj.blkid_partition_get_start.argtypes = (c_void_p, )
		self.obj.blkid_partition_get_start.restype = c_int
		return self.obj.blkid_partition_get_start(par.ptr)

	def partition_get_size(self, par: BlkidPartition) -> int:
		self.obj.blkid_partition_get_size.argtypes = (c_void_p, )
		self.obj.blkid_partition_get_size.restype = c_int
		return self.obj.blkid_partition_get_size(par.ptr)

	def partition_get_type(self, par: BlkidPartition) -> int:
		self.obj.blkid_partition_get_type.argtypes = (c_void_p, )
		self.obj.blkid_partition_get_type.restype = c_int
		return self.obj.blkid_partition_get_type(par.ptr)

	def partition_get_type_string(self, par: BlkidPartition) -> str:
		self.obj.blkid_partition_get_type_string.argtypes = (c_void_p, )
		self.obj.blkid_partition_get_type_string.restype = c_char_p
		return self.obj.blkid_partition_get_type_string(par.ptr).decode()

	def partition_get_flags(self, par: BlkidPartition) -> int:
		self.obj.blkid_partition_get_flags.argtypes = (c_void_p, )
		self.obj.blkid_partition_get_flags.restype = c_int
		return self.obj.blkid_partition_get_flags(par.ptr)

	def partition_is_logical(self, par: BlkidPartition) -> bool:
		self.obj.blkid_partition_is_logical.argtypes = (c_void_p, )
		self.obj.blkid_partition_is_logical.restype = c_int
		return bool(self.obj.blkid_partition_is_logical(par.ptr))

	def partition_is_extended(self, par: BlkidPartition) -> bool:
		self.obj.blkid_partition_is_extended.argtypes = (c_void_p, )
		self.obj.blkid_partition_is_extended.restype = c_int
		return bool(self.obj.blkid_partition_is_extended(par.ptr))

	def partition_is_primary(self, par: BlkidPartition) -> bool:
		self.obj.blkid_partition_is_primary.argtypes = (c_void_p, )
		self.obj.blkid_partition_is_primary.restype = c_int
		return bool(self.obj.blkid_partition_is_primary(par.ptr))

	def parttable_get_type(self, tab: BlkidPartTable) -> str:
		self.obj.blkid_parttable_get_type.argtypes = (c_void_p, )
		self.obj.blkid_parttable_get_type.restype = c_char_p
		return self.obj.blkid_parttable_get_type(tab.ptr).decode()

	def parttable_get_id(self, tab: BlkidPartTable) -> str:
		self.obj.blkid_parttable_get_id.argtypes = (c_void_p, )
		self.obj.blkid_parttable_get_id.restype = c_char_p
		return self.obj.blkid_parttable_get_id(tab.ptr).decode()

	def parttable_get_offset(self, tab: BlkidPartTable) -> int:
		self.obj.blkid_parttable_get_offset.argtypes = (c_void_p, )
		self.obj.blkid_parttable_get_offset.restype = c_int
		return self.obj.blkid_parttable_get_offset(tab.ptr)

	def parttable_get_parent(self, tab: BlkidPartTable) -> BlkidPartition:
		self.obj.blkid_parttable_get_parent.argtypes = (c_void_p, )
		self.obj.blkid_parttable_get_parent.restype = c_void_p
		return BlkidPartition(self, self.obj.blkid_parttable_get_parent(tab.ptr))

	def do_probe(self, pr: BlkidProbe) -> int:
		self.obj.blkid_do_probe.argtypes = (c_void_p, )
		self.obj.blkid_do_probe.restype = c_int
		return self.obj.blkid_do_probe(pr.ptr)

	def do_safeprobe(self, pr: BlkidProbe) -> int:
		self.obj.blkid_do_safeprobe.argtypes = (c_void_p, )
		self.obj.blkid_do_safeprobe.restype = c_int
		return self.obj.blkid_do_safeprobe(pr.ptr)

	def do_fullprobe(self, pr: BlkidProbe) -> int:
		self.obj.blkid_do_fullprobe.argtypes = (c_void_p, )
		self.obj.blkid_do_fullprobe.restype = c_int
		return self.obj.blkid_do_fullprobe(pr.ptr)

	def probe_numof_values(self, pr: BlkidProbe) -> int:
		self.obj.blkid_probe_numof_values.argtypes = (c_void_p, )
		self.obj.blkid_probe_numof_values.restype = c_int
		return self.obj.blkid_probe_numof_values(pr.ptr)

	def probe_get_value(self, pr: BlkidProbe, num: int) -> tuple[int, str, str, int]:
		self.obj.blkid_probe_get_value.argtypes = (c_void_p, c_int, c_void_p, c_void_p, c_void_p, )
		self.obj.blkid_probe_get_value.restype = c_int
		name = POINTER(c_char_p)
		data = POINTER(c_char_p)
		len = POINTER(c_uint64)
		ret = self.obj.blkid_probe_get_value(pr.ptr, num, name, data, len)
		return (ret, name, data, len)

	def probe_lookup_value(self, pr: BlkidProbe, name: str, data: str, len: int) -> int:
		self.obj.blkid_probe_lookup_value.argtypes = (c_void_p, c_char_p, c_void_p, c_void_p, )
		self.obj.blkid_probe_lookup_value.restype = c_int
		data = POINTER(c_char_p)
		len = POINTER(c_uint64)
		return self.obj.blkid_probe_lookup_value(pr, name, data, len)

	def probe_has_value(self, pr: BlkidProbe, name: str) -> int:
		self.obj.blkid_probe_has_value.argtypes = (c_void_p, c_char_p, )
		self.obj.blkid_probe_has_value.restype = c_int
		return self.obj.blkid_probe_has_value(pr.ptr, name)

	def do_wipe(self, pr: BlkidProbe, dryrun: bool=False) -> int:
		self.obj.blkid_do_wipe.argtypes = (c_void_p, c_int, )
		self.obj.blkid_do_wipe.restype = c_int
		return self.obj.blkid_do_wipe(pr.ptr, dryrun)

	def wipe_all(self, pr: BlkidProbe) -> int:
		self.obj.blkid_wipe_all.argtypes = (c_void_p, )
		self.obj.blkid_wipe_all.restype = c_int
		return self.obj.blkid_wipe_all(pr.ptr)

	def probe_step_back(self, pr: BlkidProbe) -> int:
		self.obj.blkid_probe_step_back.argtypes = (c_void_p, )
		self.obj.blkid_probe_step_back.restype = c_int
		return self.obj.blkid_probe_step_back(pr.ptr)
