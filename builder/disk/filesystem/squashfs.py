import os
import logging
from builder.disk.filesystem.creator import FileSystemImageCreator
log = logging.getLogger(__name__)


class SquashFSCreator(FileSystemImageCreator):
	def copy(self):
		cmds: list[str] = ["mksquashfs"]
		if self.fstype != "squashfs":
			raise RuntimeError(f"unsupported fs {self.fstype}")
		if "path" not in self.config:
			raise RuntimeError(f"no path specified")
		path: str = self.config["path"]
		if path.startswith("/"): path = "." + path
		real_path = os.path.join(self.ctx.get_rootfs(), path)
		cmds.extend([real_path, self.device])
		cmds.append("-not-reproducible")
		cmds.extend(["-all-time", "now"])
		cmds.extend(["-mkfs-time", "now"])
		if "args" in self.config:
			cmds.extend(self.config["args"])
		self.setup_image()
		ret = self.ctx.run_external(cmds)
		if ret != 0: raise OSError("mksquash failed")
