import os
from logging import getLogger
from builder.lib.blkid import Blkid
from builder.disk.layout.gpt.types import DiskTypesGPT
from builder.disk.content import ImageContentBuilder
from builder.lib.config import ArchBuilderConfigError
from builder.lib.mount import MountPoint
from builder.lib.utils import path_to_name
log = getLogger(__name__)


class FileSystemBuilder(ImageContentBuilder):
	blkid: Blkid = Blkid()
	fstype_map: dict = {
		"fat12": "vfat",
		"fat16": "vfat",
		"fat32": "vfat",
	}

	def proc_cmdline_root(self, cfg: dict, mnt: MountPoint):
		ccfg = self.builder.ctx.config_orig
		mnt.remove_option("ro")
		mnt.remove_option("rw")
		for opt in mnt.option:
			if opt.startswith("x-"):
				mnt.option.remove(opt)
		if "kernel" not in ccfg: ccfg["kernel"] = {}
		kern = ccfg["kernel"]
		if "cmdline" not in kern: kern["cmdline"] = []
		cmds: list[str] = kern["cmdline"]
		if any(cmdline.startswith("root=") for cmdline in cmds):
			raise ArchBuilderConfigError("root already set in cmdline")
		if mnt.target != "/":
			log.warning(f"root target is not / ({mnt.target})")
		if not mnt.source.startswith("/") and "=" not in mnt.source:
			log.warning(f"bad root source ({mnt.source})")
		ecmds = [
			"ro", "rootwait",
			f"root={mnt.source}",
		]
		if mnt.fstype != "none":
			ecmds.append(f"rootfstype={mnt.fstype}")
		if len(mnt.option) > 0:
			ecmds.append(f"rootflags={mnt.options}")
		scmds = " ".join(ecmds)
		log.debug(f"add root cmdline {scmds}")
		cmds.extend(ecmds)
		self.builder.ctx.resolve_subscript()

	def resolve_dev_tag(self, dev: str, mnt: MountPoint):
		dev = dev.upper()
		match dev:
			case "UUID" | "LABEL":
				log.warning(f"'{dev}=' maybe unsupported by kernel")
				if dev in self.properties: val = self.properties[dev]
				else: val = self.blkid.get_tag_value(None, dev, self.builder.device)
			case "PARTUUID" | "PARTLABEL":
				val = self.properties[dev] if dev in self.properties else None
			case _: raise ArchBuilderConfigError(f"unsupported device type {dev}")
		if not val: raise ArchBuilderConfigError(f"property {dev} not found")
		mnt.source = f"{dev}={val}"

	def proc_grow(self, cfg: dict, mnt: MountPoint):
		root = self.builder.ctx.get_rootfs()
		if "ptype" not in cfg:
			log.warning("no partition type set, grow filesystem only")
			mnt.option.append("x-systemd.growfs")
			return
		ptype = DiskTypesGPT.lookup_one_uuid(cfg["ptype"])
		if ptype is None: raise ArchBuilderConfigError(f"unknown type {cfg['ptype']}")
		mnt.option.append("x-systemd.growfs")
		conf = "grow-%s.conf" % path_to_name(mnt.target)
		repart = os.path.join(root, "etc/repart.d", conf)
		os.makedirs(os.path.dirname(repart), mode=0o0755, exist_ok=True)
		fsname, fsuuid = None, None
		dev = self.builder.device
		if "fsname" in cfg: fsname = cfg["fsname"]
		if "fsuuid" in cfg: fsuuid = cfg["fsuuid"]
		if fsname is None: fsname = self.blkid.get_tag_value(None, "LABEL", dev)
		if fsuuid is None: fsuuid = self.blkid.get_tag_value(None, "UUID", dev)
		with open(repart, "w") as f:
			f.write("[Partition]\n")
			f.write(f"Type={ptype}\n")
			f.write(f"Format={mnt.fstype}\n")
			if fsname: f.write(f"Label={fsname}\n")
			if fsuuid: f.write(f"UUID={fsuuid}\n")
		log.info(f"generated repart config {repart}")

	def proc_fstab(self, cfg: dict):
		mnt = MountPoint()
		ccfg = self.builder.ctx.config
		fstab = cfg["fstab"] if "fstab" in cfg else {}
		rfstab = ccfg["fstab"] if "fstab" in ccfg else {}
		mnt.target = cfg["mount"]
		mnt.fstype = cfg["fstype"]
		dev = None
		if "dev" in fstab: dev = fstab["dev"]
		if "dev" in rfstab: dev = rfstab["dev"]
		if dev: self.resolve_dev_tag(dev, mnt)
		if mnt.target == "/": mnt.fs_passno = 1
		elif not mnt.virtual: mnt.fs_passno = 2
		if "target" in fstab: mnt.target = fstab["target"]
		if "source" in fstab: mnt.source = fstab["source"]
		if "type" in fstab: mnt.fstype = fstab["type"]
		if "dump" in fstab: mnt.fs_freq = fstab["dump"]
		if "passno" in fstab: mnt.fs_passno = fstab["passno"]
		if "flags" in fstab:
			flags = fstab["flags"]
			if type(flags) is str: mnt.options = flags
			elif type(flags) is list: mnt.option = flags
			else: raise ArchBuilderConfigError("bad flags")
		if mnt.source is None or mnt.target is None:
			raise ArchBuilderConfigError("incomplete fstab")
		if len(self.builder.ctx.fstab.find_target(mnt.target)) > 0:
			raise ArchBuilderConfigError(f"duplicate fstab target {mnt.target}")
		if mnt.fstype in self.fstype_map:
			mnt.fstype = self.fstype_map[mnt.fstype]
		if "grow" in cfg and cfg["grow"]:
			self.proc_grow(cfg, mnt)
		mnt.fixup()
		log.debug(f"add fstab entry {mnt}")
		self.builder.ctx.fstab.append(mnt)
		self.builder.ctx.fsmap[mnt.source] = self.builder.device
		if "boot" in fstab and fstab["boot"]:
			self.proc_cmdline_root(cfg, mnt.clone())

	def format(self, fstype: str):
		from builder.disk.filesystem.creator import FileSystemCreators
		FileSystemCreators.init()
		t = FileSystemCreators.find_builder(fstype)
		if t is None: raise ArchBuilderConfigError(f"unsupported fs type {fstype}")
		creator = t(fstype, self, self.builder.config)
		creator.create()

	def build(self):
		cfg = self.builder.config
		if "fstype" not in cfg:
			raise ArchBuilderConfigError("fstype not set")
		fstype = cfg["fstype"]
		self.format(fstype)
		if "mount" in cfg:
			self.proc_fstab(cfg)
