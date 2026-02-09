from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models.zip_profile import Agencies, ZipProfiles


async def get_agencies(db: AsyncSession, zip_code: str) -> dict | None:
    """Get agency by zip_code. Gets agency_code from zip_profiles, then gets agency by code."""
    # First, get zip_profiles by zip_code
    zip_result = await db.execute(
        select(ZipProfiles).where(ZipProfiles.zip_code == zip_code)
    )
    zip_profiles = zip_result.scalars().all()
    
    # Filter out zip_profiles with null agency_code and get list of agency codes
    agency_codes = [
        profile.agency_code 
        for profile in zip_profiles 
        if profile.agency_code is not None
    ]
    
    # If no agency codes found, return None
    if not agency_codes:
        return None
    
    # Select the first agency_code
    agency_code = agency_codes[0]
    
    # Get agency by agency_code
    agency_result = await db.execute(
        select(Agencies).where(Agencies.code == agency_code)
    )
    agencies = agency_result.scalars().all()
    
    # If no agencies found, return None
    if not agencies:
        return None
    
    # Get the first agency if multiple exist
    agency = agencies[0]
    
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
