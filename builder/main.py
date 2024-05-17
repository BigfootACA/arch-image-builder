import os
import logging
from sys import stdout
from locale import setlocale, LC_ALL
from argparse import ArgumentParser
from builder.build import bootstrap
from builder.lib import config, utils
from builder.lib.context import ArchBuilderContext
log = logging.getLogger(__name__)


def parse_arguments(ctx: ArchBuilderContext):
	parser = ArgumentParser(
		prog="arch-image-builder",
		description="Build flashable image for Arch Linux",
	)
	parser.add_argument("-c", "--config",      help="Select config to build", required=True, action='append')
	parser.add_argument("-o", "--workspace",   help="Set workspace for builder", default=ctx.work)
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

	# collect configs path
	configs = []
	for conf in args.config:
		configs.extend(conf.split(","))

	# load and populate configs
	config.load_configs(ctx, configs)
	config.populate_config(ctx)

	# build folder: {TOP}/build/{TARGET}
	ctx.work = os.path.realpath(os.path.join(args.workspace, ctx.target))


def init_environment():
	# set user agent for pacman (some mirrors requires)
	os.environ["HTTP_USER_AGENT"] = "arch-image-builder(pacman) pyalpm"

	# set to default language to avoid problems
	os.environ["LANG"] = "C"
	os.environ["LANGUAGE"] = "C"
	os.environ["LC_ALL"] = "C"
	setlocale(LC_ALL, "C")


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
	init_environment()
	ctx = ArchBuilderContext()
	ctx.dir = os.path.realpath(os.path.join(os.path.dirname(__file__), os.path.pardir))
	ctx.work = os.path.realpath(os.path.join(ctx.dir, "build"))
	parse_arguments(ctx)
	log.info(f"source tree folder: {ctx.dir}")
	log.info(f"workspace folder:   {ctx.work}")
	log.info(f"build target name:  {ctx.target}")
	bootstrap.build_rootfs(ctx)
