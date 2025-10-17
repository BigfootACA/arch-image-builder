from logging import getLogger
from builder.lib.context import ArchBuilderContext
from builder.build.systemd_boot import proc_systemd_boot
from builder.build.embloader import proc_embloader
from builder.build.extlinux import proc_extlinux
from builder.build.grub import proc_grub
log = getLogger(__name__)

methods = {
	"systemd-boot": proc_systemd_boot,
	"embloader": proc_embloader,
	"extlinux": proc_extlinux,
	"grub": proc_grub,
}

def proc_bootloader(ctx: ArchBuilderContext):
	for method in ctx.get("bootloader.method", []):
		if method not in methods:
			raise ValueError(f"unsupported bootloader method {method}")
		methods[method](ctx)
