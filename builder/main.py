import os
import logging
from sys import stdout
from argparse import ArgumentParser
from builder.build import bootstrap, package
from builder.lib import config, utils
from builder.lib.context import ArchBuilderContext
log = logging.getLogger(__name__)


def parse_arguments(ctx: ArchBuilderContext):
	parser = ArgumentParser(
		prog="arch-image-builder",
		description="Build flashable image for Arch Linux",
	)
	parser.add_argument("-C", "--clean",       help="Clean workspace before build", default=False, action='store_true')
	parser.add_argument("-p", "--preset",      help="Select preset to create package")
	parser.add_argument("-c", "--config",      help="Select config to build", action='append')
	parser.add_argument("-m", "--mirror",      help="Select mirror to download package", action='append')
	parser.add_argument("-o", "--workspace",   help="Set workspace for builder", default=ctx.work)
	parser.add_argument("-a", "--artifacts",   help="Set artifacts folder for builder", default=ctx.artifacts)
	parser.add_argument("-d", "--debug",       help="Enable debug logging", default=False, action='store_true')
	parser.add_argument("-G", "--no-gpgcheck", help="Disable GPG check", default=False, action='store_true')
	parser.add_argument("-r", "--repack",      help="Repack rootfs only", default=False, action='store_true')
	args = parser.parse_args()

	# debug logging
	if args.debug:
		logging.root.setLevel(logging.DEBUG)
		log.debug("enabled debug logging")

	if args.no_gpgcheck: ctx.gpgcheck = False
	if args.repack: ctx.repack = True
	if args.clean: ctx.clean = True
	if ctx.clean and ctx.repack:
		raise RuntimeError("clean and repack should not be used at the same time")

	# collect configs path
	configs = []
	if args.config:
		for conf in args.config:
			configs.extend(conf.split(","))

	# load preset config for build package
	if args.preset:
		config.load_preset(ctx, args.preset)
		pcfgs = ctx.get("package.configs", [])
		configs.extend(pcfgs)

	if args.mirror:
		for mirror in args.mirror:
			configs.extend([f"mirrors/{name}" for name in mirror.split(",")])

	# load configs
	config.load_configs(ctx, configs)
	config.fill_base_options(ctx)

	# build folder: {TOP}/build/{TARGET}
	ctx.work = os.path.realpath(os.path.join(args.workspace, ctx.target))

	# populate configs
	config.populate_config(ctx)

	if args.artifacts:
		ctx.artifacts = os.path.realpath(args.artifacts)


def check_system():
	# why not root?
	if os.getuid() != 0:
		raise PermissionError("this tool can only run as root")

	# always need pacman
	if not utils.have_external("pacman"):
		raise FileNotFoundError("pacman not found")


def main():
	logging.basicConfig(stream=stdout, level=logging.INFO)
	check_system()
	utils.init_environment()
	ctx = ArchBuilderContext()
	ctx.dir = os.path.realpath(os.path.join(os.path.dirname(__file__), os.path.pardir))
	ctx.work = os.path.realpath(os.path.join(ctx.dir, "build"))
	ctx.artifacts = ctx.work
	parse_arguments(ctx)
	log.info(f"package version:    {ctx.version}")
	log.info(f"source tree folder: {ctx.dir}")
	log.info(f"workspace folder:   {ctx.work}")
	log.info(f"build target name:  {ctx.target}")
	bootstrap.build_rootfs(ctx)
	if ctx.preset:
		package.done_package(ctx)
