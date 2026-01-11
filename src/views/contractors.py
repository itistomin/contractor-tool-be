from fastapi import (
    APIRouter,
    Depends,
)


from security.authorization import get_aws_user
from database.connection import get_db

from database.queries.contractors import get_profile_by_zip


router = APIRouter(
    prefix="/contractors",
    tags=["contractors"],
)


@router.get("/zip")
async def auth_user(
    zip_code: int,
    db = Depends(get_db),
    # user = Depends(get_aws_user),
):
    return await get_profile_by_zip(db, zip_code)
