from builder.disk.content import ImageContentBuilder
from builder.disk.layout.build import DiskLayoutBuilder
from builder.disk.filesystem.build import FileSystemBuilder
from builder.disk.abootimg import AndroidBootBuilder
from builder.disk.file import ImageFileBuilder


types: list[tuple[str, type[ImageContentBuilder]]] = [
	("disk",       DiskLayoutBuilder),
	("filesystem", FileSystemBuilder),
	("aboot",      AndroidBootBuilder),
	("avndboot",   AndroidBootBuilder),
	("image",      ImageFileBuilder),
]
