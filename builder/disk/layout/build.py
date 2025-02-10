from builder.disk.content import ImageContentBuilder
from builder.disk.layout.disk import Disk
from builder.disk.image import ImageBuilder
from builder.lib.config import ArchBuilderConfigError
from builder.lib.context import ArchBuilderContext


class DiskLayoutBuilder(ImageContentBuilder):
	ctx: ArchBuilderContext
	builders: list[ImageBuilder]

	def build(self):
		self.ctx = self.builder.ctx
		cfg = self.builder.config
		if "layout" not in cfg:
			raise ArchBuilderConfigError("layout not set")
		if "partitions" not in cfg:
			raise ArchBuilderConfigError("partitions not set")
		layout = Disk.find_layout(cfg["layout"])
		if layout is None:
			raise ArchBuilderConfigError(f"layout {layout} not found")
		disk = layout(
			path=self.builder.device,
			sector=self.builder.sector
		)
		disk.create()
		disk.set_from(cfg)
		self.builders = []
		for part in cfg["partitions"]:
			p = disk.add_partition_from(part)
			if "type" in part:
				b = ImageBuilder(self.ctx, part, self.builder)
				if p.partlabel: b.properties["PARTLABEL"] = p.partlabel
				if p.partuuid: b.properties["PARTUUID"] = p.partuuid
				b.sector, b.offset, b.size = disk.sector, p.start, p.size
				self.builders.append(b)
		disk.save()
		for builder in self.builders:
			builder.build()

	def build_post(self):
		for builder in self.builders:
			builder.build_post()
