from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models.zip_profile import Agencies


async def get_agencies(db: AsyncSession, agency_code: str) -> dict | None:
    """Get agency by agency_code and return as dictionary."""
    result = await db.execute(
        select(Agencies).where(Agencies.code == agency_code)
    )
    agency = result.scalar_one_or_none()
    
    if agency is None:
        return None
    
    return {
        "id": agency.id,
        "code": agency.code,
        "name": agency.name,
        "phone": agency.phone,
        "website": agency.website,
        "to_apply_url": agency.to_apply_url,
        "notes": agency.notes,
        "created_at": agency.created_at.isoformat() if agency.created_at else None,
        "updated_at": agency.updated_at.isoformat() if agency.updated_at else None,
    }
