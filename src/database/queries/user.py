from sqlalchemy import select, insert
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import User


async def get_user_by_email(db: AsyncSession, email: str) -> User:
    result = await db.execute(
        select(User).where(User.email == email)
    )
    return result.scalar_one_or_none()


async def get_users_by_cognito_group(db: AsyncSession, group_name: str) -> list[User]:
    """Return all users whose cognito_group equals the given group name."""
    result = await db.execute(
        select(User).where(User.cognito_group == group_name)
    )
    return list(result.scalars().all())


async def create_user(
    db: AsyncSession,
    email: str,
    username: str,
    cognito_group: str | None = None,
) -> User:
    await db.execute(
        insert(User).values(
            email=email,
            full_name=username,
            cognito_group=cognito_group,
        )
    )
    await db.commit()
    return await get_user_by_email(db, email)


async def get_or_create_user(
    db: AsyncSession,
    email: str,
    username: str,
    cognito_group: str | None = None,
) -> User:
    user = await get_user_by_email(db, email)
    if user:
        if cognito_group is not None and user.cognito_group != cognito_group:
            user.cognito_group = cognito_group
            await db.commit()
            await db.refresh(user)
        return user
    return await create_user(db, email, username, cognito_group)
