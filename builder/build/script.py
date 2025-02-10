import os
from logging import getLogger, DEBUG
from builder.build.filesystem import chroot_run
from builder.lib.context import ArchBuilderContext
from builder.lib.config import ArchBuilderConfigError
log = getLogger(__name__)


def run_script(ctx: ArchBuilderContext, script: dict):
	ret = 0
	env: dict = None
	shell: str = script.get("shell", "bash")
	cwd: str = script.get("cwd", None)
	args = [shell]
	if "code" not in script:
		raise ArchBuilderConfigError("no script code specified")
	if "env" in script:
		env = os.environ.copy()
		for item in script["env"]:
			env[item] = script["env"]["item"]
	can_def = shell in ["sh", "bash", "dash", "zsh", "ash", "zsh"]
	if script.get("debug", log.isEnabledFor(DEBUG) if can_def else False):
		args.append("-x")
	if script.get("nofail", can_def):
		args.append("-e")
	log.debug(f"running custom script\n{script["code"]}")
	if script.get("chroot", False):
		ret = chroot_run(ctx, args, cwd, env, script["code"])
	else:
		ret = ctx.run_external(args, cwd, env, script["code"])
	if ret !=0: raise ArchBuilderConfigError(f"script run failed: {ret}")


def run_scripts(ctx: ArchBuilderContext, stage: str = None):
	scripts: list[dict] = []
	for script in ctx.config.get("scripts", []):
		cs = script.get("stage")
		if cs != stage: continue
		scripts.append(script)
	scripts.sort(key=lambda script: script.get("priority", 0x100000000))
	for script in scripts:
		run_script(ctx, script)
