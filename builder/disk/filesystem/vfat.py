from builder.disk.filesystem.creator import FileSystemCreator
from builder.lib.config import ArchBuilderConfigError


class FatCreator(FileSystemCreator):
	def create(self):
		cmds: list[str] = ["mkfs.fat"]
		bits: int = 0
		match self.fstype:
			case "vfat": bits = 32
			case "fat12": bits = 12
			case "fat16": bits = 16
			case "fat32": bits = 32
			case "msdos": bits = 16
			case _: raise ArchBuilderConfigError("unknown fat type")
		cmds.append(f"-F{bits}")
		if "fsname" in self.config: cmds.extend(["-n", self.config["fsname"]])
		if "fsvolid" in self.config: cmds.extend(["-i", self.config["fsvolid"]])
		cmds.extend(["-S", str(self.builder.builder.sector)])
		cmds.append(self.device)
		ret = self.ctx.run_external(cmds)
		if ret != 0: raise OSError("mkfs.fat failed")
