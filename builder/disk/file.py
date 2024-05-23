import os
from logging import getLogger
from builder.disk.content import ImageContentBuilder
from builder.lib.config import ArchBuilderConfigError
log = getLogger(__name__)


class ImageFileBuilder(ImageContentBuilder):
	def build(self):
		cmds = ["dd"]
		ctx = self.builder.ctx
		cfg = self.builder.config
		if "file" not in cfg:
			raise ArchBuilderConfigError("file not set")
		file: str = cfg["file"]
		if file.startswith("/"): file = file[1:]
		path = os.path.join(ctx.get_rootfs(), file)
		if not os.path.exists(path):
			raise FileNotFoundError(f"image file {path} not found")
		cmds.append("status=progress")
		cmds.append(f"if={path}")
		cmds.append(f"of={self.builder.device}")
		cmds.append(f"bs={self.builder.sector}")
		log.info(f"start writing image file {path}")
		ret = ctx.run_external(cmds)
		if ret != 0: raise OSError("dd failed")
		log.info(f"write image file {path} done")
