import os
import logging
from builder.disk.filesystem.creator import FileSystemImageCreator
log = logging.getLogger(__name__)


class EROFSCreator(FileSystemImageCreator):
	def copy(self):
		cmds: list[str] = ["mkfs.erofs"]
		if self.fstype != "erofs":
			raise RuntimeError(f"unsupported fs {self.fstype}")
		if "path" not in self.config:
			raise RuntimeError(f"no path specified")
		path: str = self.config["path"]
		if path.startswith("/"): path = "." + path
		real_path = os.path.join(self.ctx.get_rootfs(), path)
		if "args" in self.config:
			cmds.extend(self.config["args"])
		cmds.extend([self.device, real_path])
		self.setup_image()
		ret = self.ctx.run_external(cmds)
		if ret != 0: raise OSError("mkfs.erofs failed")
