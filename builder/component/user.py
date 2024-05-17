from logging import getLogger
from builder.lib.config import ArchBuilderConfigError
from builder.lib.context import ArchBuilderContext
log = getLogger(__name__)


def parse_usergroup_item(
	ctx: ArchBuilderContext,
	item: str | int,
	group: bool = False
) -> int:
	if type(item) is int:
		return int(item)
	elif type(item) is str:
		if group:
			user = ctx.passwd.lookup_name(item)
			if user is None: raise ArchBuilderConfigError(
				f"user {item} not found"
			)
			return user.gid
		else:
			grp = ctx.group.lookup_name(item)
			if grp is None: raise ArchBuilderConfigError(
				f"group {item} not found"
			)
			return grp.gid
	else: raise ArchBuilderConfigError("bad owner type")


def parse_owner(ctx: ArchBuilderContext, owner: str) -> tuple[int, int]:
	if ":" in owner:
		i = owner.find(":")
		uid = parse_usergroup_item(ctx, owner[0:i], False)
		gid = parse_usergroup_item(ctx, owner[i+1:], True)
	else:
		uid = parse_usergroup_item(ctx, owner, False)
		user = ctx.passwd.lookup_uid(uid)
		if user is None: raise ArchBuilderConfigError(
			f"user {user} not found"
		)
		gid = user.gid
	return uid, gid


def parse_usergroup_from(
	ctx: ArchBuilderContext,
	node: dict,
	group: bool = False,
	default: int = 0
) -> int:
	kid = "uid" if not group else "gid"
	kname = "owner" if not group else "group"
	if kid in node: return int(node[kid])
	if kname in node: return parse_usergroup_item(
		ctx, node[kname], group
	)
	return default


def parse_user_from(
	ctx: ArchBuilderContext,
	node: dict,
	default: tuple[int, int] = (0, -1)
) -> tuple[int, int]:
	if "owner" in node: return parse_owner(ctx, node["owner"])
	uid = parse_usergroup_from(ctx, node, False, default[0])
	gid = parse_usergroup_from(ctx, node, True, default[1])
	if gid == -1:
		user = ctx.passwd.lookup_uid(uid)
		if user is None: raise ArchBuilderConfigError(
			f"user {user} not found"
		)
		gid = user.gid
	return uid, gid
