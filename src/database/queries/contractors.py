from sqlalchemy import select, insert
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import ZipProfiles


async def get_profile_by_zip(
    db,
    zip_code: str,
    city: str | None = None,
    fuel_type: str | None = None,
):
    query = select(ZipProfiles).where(ZipProfiles.zip_code == zip_code)
    if city:
        query = query.where(ZipProfiles.city == city)
    if fuel_type:
        query = query.where(ZipProfiles.fuel_type == fuel_type)

    result = await db.execute(query)
    return result.scalars().all()
