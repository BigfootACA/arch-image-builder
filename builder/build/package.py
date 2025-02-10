import os
import logging
from builder.lib.context import ArchBuilderContext
from builder.lib.config import ArchBuilderConfigError
log = logging.getLogger(__name__)


def done_package(ctx: ArchBuilderContext):
	file: str = ctx.get("package.file", "")
	out = file
	if not out.startswith("/"):
		if not os.path.exists(ctx.artifacts):
			os.makedirs(ctx.artifacts, mode=0o755, exist_ok=True)
		out = os.path.join(ctx.artifacts, file)
	if not out.endswith(".7z"):
		raise ArchBuilderConfigError("current only supports 7z")
	log.info(f"creating package {file}")
	args = ["7z", "a", "-ms=on", "-mx=9", out, "."]
	ret = ctx.run_external(args, cwd=ctx.get_output())
	if ret != 0: raise OSError("create package failed")
	log.info(f"created package at {out}")
