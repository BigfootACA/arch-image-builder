from builder.disk.filesystem.creator import FileSystemCreator
from builder.disk.filesystem.btrfs import BtrfsCreator
from builder.disk.filesystem.ext4 import EXT4Creator
from builder.disk.filesystem.vfat import FatCreator
from builder.disk.filesystem.squashfs import SquashFSCreator
from builder.disk.filesystem.erofs import EROFSCreator


types: list[tuple[str, type[FileSystemCreator]]] = [
	("ext2",       EXT4Creator),
	("ext3",       EXT4Creator),
	("ext4",       EXT4Creator),
	("vfat",       FatCreator),
	("fat12",      FatCreator),
	("fat16",      FatCreator),
	("fat32",      FatCreator),
	("msdos",      FatCreator),
	("btrfs",      BtrfsCreator),
	("squashfs",   SquashFSCreator),
	("erofs",      EROFSCreator),
]
