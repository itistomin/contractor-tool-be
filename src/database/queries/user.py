from sqlalchemy import select, insert
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import User


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(
        select(User).where(User.email == email)
    )
    return result.scalar_one_or_none()


async def create_user(db: AsyncSession, email: str, username: str) -> User:
    await db.execute(
        insert(User).values(email=email, full_name=username)
    )
    await db.commit()
    return await get_user_by_email(db, email)


async def get_or_create_user(db: AsyncSession, email: str, username: str) -> User:
    user = await get_user_by_email(db, email)
    if user:
        return user
    return await create_user(db, email, username)
