import os
import logging
from sys import stderr
from argparse import ArgumentParser
from builder.lib import json, utils
log = logging.getLogger(__name__)


runners = {
	"aarch64": "ubuntu-24.04-arm",
	"x86_64": "ubuntu-24.04",
}

class WorkflowHelper:
	"""
	Top tree folder
	"""
	dir: str = None

	"""
	List presets
	"""
	list_presets: bool = False

	"""
	Filter by CPU architecture
	"""
	filter_arch: list[str] = []

	"""
	Filter by auto run
	"""
	filter_auto: bool = False


def parse_arguments(ctx: WorkflowHelper):
	parser = ArgumentParser(
		prog="workflow-helper",
		description="Workflow helper for arch-image-builder",
	)
	parser.add_argument("-d", "--debug",       help="Enable debug logging", default=False, action='store_true')
	parser.add_argument("--list-presets",      help="List presets", default=False, action='store_true')
	parser.add_argument("--filter-arch",       help="Filter with CPU architecture")
	parser.add_argument("--filter-auto",       help="Filter with auto", default=False, action='store_true')
	args = parser.parse_args()

	# debug logging
	if args.debug:
		logging.root.setLevel(logging.DEBUG)
		log.debug("enabled debug logging")

	ctx.list_presets = args.list_presets

	if args.filter_arch:
		ctx.filter_arch.append(args.filter_arch)

	ctx.filter_auto = args.filter_auto


def list_presets(ctx: WorkflowHelper):
	results: list[dict[str, str]] = []
	presets = os.path.join(ctx.dir, "configs", "presets")
	for preset in os.listdir(presets):
		if not preset.endswith((".yaml", ".yml", ".jsn", ".json")):
			continue
		path = os.path.join(presets, preset)
		name = preset[:preset.rfind(".")]
		if not os.path.isfile(path):
			continue
		log.debug(f"found config {name}")
		try:
			config = utils.load_simple(path)
		except:
			log.warning(f"load {name} failed", exc_info=True)
		if "workflows" not in config:
			log.debug(f"skip {name} because no workflows")
			continue
		if "arch" not in config["workflows"]:
			log.debug(f"skip {name} because no workflows.arch")
			continue
		if ctx.filter_arch and config["workflows"]["arch"] not in ctx.filter_arch:
			log.debug(f"skip {name} because workflows.arch mismatch")
			continue
		if ctx.filter_auto:
			if "auto" not in config["workflows"]:
				log.debug(f"skip {name} because no workflows.auto")
				continue
			if not config["workflows"]["auto"]:
				log.debug(f"skip {name} because workflows.auto mismatch")
				continue
		results.append({
			"preset": name,
			"arch": config["workflows"]["arch"],
			"runner": runners[config["workflows"]["arch"]],
		})
	print(json.dumps(results))


def main():
	logging.basicConfig(stream=stderr, level=logging.INFO)
	utils.init_environment()
	ctx = WorkflowHelper()
	ctx.dir = os.path.realpath(os.path.join(os.path.dirname(__file__), os.path.pardir))
	parse_arguments(ctx)
	if ctx.list_presets:
		list_presets(ctx)
	else:
		raise RuntimeError("no action specified")
