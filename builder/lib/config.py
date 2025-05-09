import os
from logging import getLogger
from builder.lib import json
from builder.lib.cpu import cpu_arch_compatible
from builder.lib.utils import load_simple
from builder.lib.context import ArchBuilderContext
log = getLogger(__name__)


class ArchBuilderConfigError(Exception):
	pass


def _dict_merge(dst: dict, src: dict):
	"""
	Merge two dict with override
	"""
	for key in src.keys():
		st = type(src[key])
		if key in dst and st is type(dst[key]):
			if st == list:
				dst[key].extend(src[key])
				continue
			if st == dict:
				_dict_merge(dst[key], src[key])
				continue
		dst[key] = src[key]


def load_config_file(ctx: ArchBuilderContext, path: str):
	"""
	Load one config (yaml/json) to context
	"""
	loaded = load_simple(path)
	def _proc_include(inc: str | list[str]):
		pt = type(inc)
		if pt is str: inc = [inc]
		elif pt is list: pass
		else: raise ArchBuilderConfigError("bad type for also")
		load_configs(ctx, inc)
	if loaded is None: return
	if "+also" in loaded:
		_proc_include(loaded["+also"])
		loaded.pop("+also")
	if ctx.config is None:
		log.debug(f"use {path} as current config")
		ctx.config = loaded
	else:
		log.debug(f"merge {path} into current config")
		_dict_merge(ctx.config, loaded)
	if "+then" in loaded:
		_proc_include(loaded["+then"])
		loaded.pop("+then")

def fill_base_options(ctx: ArchBuilderContext):
	if "target" not in ctx.config:
		raise ArchBuilderConfigError("no target set")
	if "arch" not in ctx.config:
		raise ArchBuilderConfigError("no cpu arch set")
	ctx.target = ctx.config["target"]
	ctx.tgt_arch = ctx.config["arch"]
	if ctx.tgt_arch == "any" or ctx.cur_arch == "any":
		raise ArchBuilderConfigError("bad cpu arch value")

def populate_config(ctx: ArchBuilderContext):
	ctx.config["work"] = ctx.work
	ctx.config["rootfs"] = ctx.get_rootfs()
	ctx.config["output"] = ctx.get_output()
	ctx.config["mount"] = ctx.get_mount()
	ctx.finish_config()
	ctx.resolve_subscript()
	if not cpu_arch_compatible(ctx.tgt_arch, ctx.cur_arch):
		log.warning(
			f"current cpu arch {ctx.cur_arch} is not compatible to {ctx.tgt_arch}, "
			"you may need qemu-user-static-binfmt to run incompatible executables",
		)
	jstr = json.dumps(ctx.config, indent=2)
	log.debug(f"populated config:\n {jstr}")


def load_configs(ctx: ArchBuilderContext, configs: list[str]):
	"""
	Load multiple config to context
	"""
	loaded = 0
	for config in configs:
		success = False
		for suffix in ["yml", "yaml", "jsn", "json"]:
			fn = f"{config}.{suffix}"
			path = os.path.join(ctx.dir, "configs", fn)
			if os.path.exists(path):
				load_config_file(ctx, path)
				loaded += 1
				success = True
		if not success:
			raise FileNotFoundError(f"config {config} not found")
	if loaded > 0:
		if ctx.config is None:
			raise ArchBuilderConfigError("no any config loaded")
	log.debug(f"loaded {loaded} configs")


def load_preset(ctx: ArchBuilderContext, preset: str):
	file = preset
	if not preset.startswith("/"):
		file = "presets/" + preset
	ctx.preset = True
	load_configs(ctx, [file])
	if "package" not in ctx.config:
		raise ArchBuilderConfigError("bad preset config")
	log.info(f"loaded preset {preset}")
