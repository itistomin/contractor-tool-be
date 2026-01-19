from fastapi import (
    APIRouter,
    Depends,
)


from security.authorization import get_aws_user
from database.connection import get_db

from database.queries.contractors import get_profile_by_zip
from database.queries.agencies import get_agencies as get_agencies_query


router = APIRouter(
    prefix="/contractors",
    tags=["contractors"],
)


@router.get("/")
async def auth_user(
    zip_code: str,
    city: str | None = None,
    fuel_type: str | None = None,
    db = Depends(get_db),
    # user = Depends(get_aws_user),
):
    return await get_profile_by_zip(db, zip_code, city, fuel_type)


@router.get("/agencies")
async def get_agencies(
    agency_code: str,
    db = Depends(get_db),
):
    return await get_agencies_query(db, agency_code)
