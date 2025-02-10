import os
import logging
from builder.lib.context import ArchBuilderContext
from builder.lib.config import ArchBuilderConfigError
log = logging.getLogger(__name__)


def package_7zip(ctx: ArchBuilderContext, out: str):
	args = ["7z", "a", "-ms=on", "-mx=9", out, "."]
	if os.path.exists(out) and os.path.isfile(out):
		log.debug(f"removing {out}")
		os.unlink(out)
	return ctx.run_external(args, cwd=ctx.get_output())


def package_iso(ctx: ArchBuilderContext, out: str):
	args = [
		"xorriso", "-no_rc", "-as", "mkisofs",
		"-iso-level", "3", "-full-iso9660-filenames",
		"-joliet", "-joliet-long", "-rational-rock",
	]
	args.extend(["-publisher", os.getenv("ARCH_PUBLISHER", ctx.get("package.publisher", "Unknown"))])
	args.extend(["-volid", ctx.get("package.label", ctx.get("name", "ARCHLINUX"))])
	args.extend(["-appid", ctx.get("package.app", ctx.get("name", "ArchLinux"))])
	args.extend(["-preparer", "arch-image-builder"])
	if "args" in ctx.config["package"]:
		args.extend(ctx.config["package"]["args"])
	args.extend(["-output", out])
	args.append(ctx.get_output())
	if os.path.exists(out) and os.path.isfile(out):
		log.debug(f"removing {out}")
		os.unlink(out)
	return ctx.run_external(args, cwd=ctx.get_output())


package_formats = [
	(".7z",    package_7zip),
	(".iso",   package_iso),
]

def done_package(ctx: ArchBuilderContext):
	file: str = ctx.get("package.file", "")
	out = file
	if not out.startswith("/"):
		if not os.path.exists(ctx.artifacts):
			os.makedirs(ctx.artifacts, mode=0o755, exist_ok=True)
		out = os.path.join(ctx.artifacts, file)
	packager: function[ctx: ArchBuilderContext, out: str] = None
	for p in package_formats:
		if out.lower().endswith(p[0]):
			packager = p[1]
			break
	if not packager:
		raise ArchBuilderConfigError("unsupported package format")
	log.info(f"creating package {file}")
	ret = packager(ctx, out)
	if ret != 0: raise OSError("create package failed")
	log.info(f"created package at {out}")
