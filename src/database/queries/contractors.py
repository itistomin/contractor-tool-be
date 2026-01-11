from sqlalchemy import select, insert
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import ZipProfiles


def get_profile_by_zip(db, zip_code: int):
    result = db.execute(
        select(ZipProfiles).where(ZipProfiles.zip_code == zip_code)
    )
    return result.scalar_one_or_none()
