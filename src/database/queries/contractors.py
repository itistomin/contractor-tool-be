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
    profiles = result.scalars().all()
    
    # Convert to dictionaries with agency_code included
    return [
        {
            "id": profile.id,
            "zip_code": profile.zip_code,
            "city": profile.city,
            "fuel_type": profile.fuel_type,
            "sponsored": profile.sponsored,
            "utility_type": profile.utility_type,
            "has_utility": profile.has_utility,
            "proceed_reason": profile.proceed_reason,
            "is_dec": profile.is_dec,
            "electrification_candidate": profile.electrification_candidate,
            "agency_code": profile.agency_code,
            "created_at": profile.created_at.isoformat() if profile.created_at else None,
            "updated_at": profile.updated_at.isoformat() if profile.updated_at else None,
        }
        for profile in profiles
    ]
