from fastapi import (
    APIRouter,
    Depends,
)


from security.authorization import get_aws_user
from database.connection import get_db


router = APIRouter(
    prefix="/auth",
    tags=["auth"],
)


@router.post("/user")
async def auth_user(
    user = Depends(get_aws_user),
):
    return user
