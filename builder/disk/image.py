import os
import stat
from typing import Self
from logging import getLogger
from builder.lib.loop import loop_setup
from builder.lib.utils import size_to_bytes
from builder.lib.config import ArchBuilderConfigError
from builder.lib.context import ArchBuilderContext
log = getLogger(__name__)


class ImageBuilder:
	offset: int = 0
	size: int = 0
	sector: int = 512
	type: str = None
	output: str = None
	device: str = None
	loop: bool = False
	config: dict = {}
	parent: Self = None
	ctx: ArchBuilderContext = None
	properties: dict = {}

	def create_image(self):
		if self.device: raise ValueError("device is set")
		if self.output is None: raise ArchBuilderConfigError(
			"no output set for image"
		)
		fd, recreate = -1, False
		if os.path.exists(self.output):
			st = os.stat(self.output)
			if stat.S_ISBLK(st.st_mode):
				log.debug(f"target {self.output} is a block device")
				if self.size != 0: raise ArchBuilderConfigError(
					"cannot use size field when output is a device"
				)
			elif stat.S_ISREG(st.st_mode):
				log.debug(f"target {self.output} exists, removing")
				recreate = True
				os.remove(self.output)
			else: raise ArchBuilderConfigError("target is not a file")
		else: recreate = True
		if recreate:
			try:
				if self.size == 0: raise ArchBuilderConfigError("size is not set")
				log.info(f"creating {self.output} with {self.size} bytes")
				flags = os.O_RDWR | os.O_CREAT | os.O_TRUNC
				fd = os.open(self.output, flags=flags, mode=0o0644)
				os.posix_fallocate(fd, 0, self.size)
			finally:
				if fd >= 0: os.close(fd)

	def setup_loop(self):
		target = self.output if self.parent is None else self.parent.device
		if target is None: raise ArchBuilderConfigError("no target for image")
		log.debug(f"try to create loop device from {target}")
		log.debug(f"loop offset: {self.offset}, size: {self.size}, sector {self.sector}")
		dev = loop_setup(
			path=target,
			size=self.size,
			offset=self.offset,
			block_size=self.sector,
		)
		log.info(f"created loop device {dev} from {target}")
		self.ctx.loops.append(dev)
		self.loop = True
		self.device = dev

	def __init__(
		self,
		ctx: ArchBuilderContext,
		config: dict,
		parent: Self = None
	):
		self.ctx = ctx
		self.config = config
		self.parent = parent
		self.offset = 0
		self.size = 0
		self.sector = 512
		self.loop = False
		self.properties = {}
		if "output" in config: self.output = config["output"]
		if parent is None:
			if self.output is None:
				raise ArchBuilderConfigError("no output set for image")
			if not self.output.startswith("/"):
				self.output = os.path.join(ctx.get_output(), self.output)
		else:
			if parent.device is None: raise ArchBuilderConfigError(
				"no device set for parent image"
			)
			self.sector = parent.sector
		if "sector" in config: self.sector = size_to_bytes(config["sector"])
		if "size" in config: self.size = size_to_bytes(config["size"])
		if "type" in config: self.type = config["type"]
		if self.type is None: raise ArchBuilderConfigError("no type set in image")

	def build(self):
		if self.device is None:
			if self.output:
				self.create_image()
			self.setup_loop()
		from builder.disk.content import ImageContentBuilders
		ImageContentBuilders.init()
		t = ImageContentBuilders.find_builder(self.type)
		if t is None: raise ArchBuilderConfigError(
			f"unsupported builder type {self.type}"
		)
		builder = t(self)
		builder.properties.update(self.properties)
		builder.build()


def proc_image(ctx: ArchBuilderContext):
	if "image" not in ctx.config: return
	builders: list[ImageBuilder] = []
	for image in ctx.config["image"]:
		builder = ImageBuilder(ctx, image)
		builders.append(builder)
	for builder in builders:
		builder.build()
