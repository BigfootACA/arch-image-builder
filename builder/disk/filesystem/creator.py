import os
import logging
from builder.lib.config import ArchBuilderConfigError
from builder.lib.context import ArchBuilderContext
from builder.disk.filesystem.build import FileSystemBuilder
log = logging.getLogger(__name__)


class FileSystemCreator:
	builder: FileSystemBuilder
	config: dict
	fstype: str
	device: str
	ctx: ArchBuilderContext

	def __init__(
		self,
		fstype: str,
		builder: FileSystemBuilder,
		config: dict
	):
		self.builder = builder
		self.config = config
		self.fstype = fstype
		self.device = builder.builder.device
		self.ctx = builder.builder.ctx

	def create(self): pass

	def copy(self):
		if "mount" not in self.config:
			return
		root: str = self.ctx.get_rootfs()
		mnt: str = self.ctx.get_mount()
		dir: str = self.config["mount"]
		if not dir.startswith("/"):
			raise ArchBuilderConfigError(f"invalid mount: {dir}")
		src = os.path.join(root, dir[1:])
		dst = os.path.join(mnt, dir[1:])
		log.info(f"from {src} to {dst}")
		if not os.path.ismount(dst):
			raise RuntimeError(f"destination {dst} is not a mount")
		self.ctx.do_copy(
			"rootfs" if dir == "/" else dir,
			src, dst, delete=True, no_cross=True
		)

	def auto_create_image(self) -> bool:
		return True


class FileSystemCreators:
	types: list[tuple[str, type[FileSystemCreator]]] = [
	]

	@staticmethod
	def init():
		if len(FileSystemCreators.types) > 0: return
		from builder.disk.filesystem.types import types
		FileSystemCreators.types.extend(types)

	@staticmethod
	def find_builder(name: str) -> type[FileSystemCreator]:
		return next((
			t[1]
			for t in FileSystemCreators.types
			if name == t[0]
		), None)
