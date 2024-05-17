import os
from builder.disk.filesystem.creator import FileSystemCreator


class EXT4Creator(FileSystemCreator):
	def create(self):
		cmds: list[str] = ["mke2fs"]
		if self.fstype not in ["ext2", "ext3", "ext4"]:
			raise RuntimeError(f"unsupported fs {self.fstype}")
		cmds.extend(["-t", self.fstype])
		if "fsname" in self.config: cmds.extend(["-L", self.config["fsname"]])
		if "fsuuid" in self.config: cmds.extend(["-U", self.config["fsuuid"]])
		env = os.environ.copy()
		env["MKE2FS_DEVICE_SECTSIZE"] = str(self.builder.builder.sector)
		cmds.append(self.device)
		ret = self.ctx.run_external(cmds, env=env)
		if ret != 0: raise OSError("mke2fs failed")
