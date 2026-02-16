from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import User


async def get_groups_with_users(
    db: AsyncSession,
) -> list[dict]:
    """
    Return list of groups; each group has a list of users (full_name, email).
    Group names come from User.cognito_group (user table).
    Structure: group -> list of user, group -> list of user.
    Users with no cognito_group are listed under group_name "No group".
    Each item: {"group_name": str, "users": [{"full_name": str, "email": str}]}
    """
    users_result = await db.execute(select(User).order_by(User.full_name))
    all_users = users_result.scalars().all()

    # group_name -> list of { full_name, email }
    groups_map: dict[str, list[dict]] = {}
    for u in all_users:
        group_name = u.cognito_group or "No group"
        if not group_name.strip():
            group_name = "No group"
        if group_name not in groups_map:
            groups_map[group_name] = []
        groups_map[group_name].append({"full_name": u.full_name, "email": u.email})

    return [
        {"group_name": name, "users": users_list}
        for name, users_list in sorted(groups_map.items())
    ]
