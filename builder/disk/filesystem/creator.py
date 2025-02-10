from builder.lib.context import ArchBuilderContext
from builder.disk.filesystem.build import FileSystemBuilder


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

	def copy(self): pass

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
