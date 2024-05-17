from builder.disk.filesystem.creator import FileSystemCreator


class BtrfsCreator(FileSystemCreator):
	def create(self):
		cmds: list[str] = ["mkfs.btrfs"]
		if "fsname" in self.config: cmds.extend(["-L", self.config["fsname"]])
		if "fsuuid" in self.config: cmds.extend(["-U", self.config["fsuuid"]])
		cmds.append(self.device)
		ret = self.ctx.run_external(cmds)
		if ret != 0: raise OSError("mkfs.btrfs failed")
