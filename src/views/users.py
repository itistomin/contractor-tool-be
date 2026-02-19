from fastapi import APIRouter, Depends
from pydantic import BaseModel

from database.connection import get_db
from database.queries.user import get_users_by_cognito_group
from sqlalchemy.ext.asyncio import AsyncSession


router = APIRouter(
    prefix="/users",
    tags=["users"],
)

AUDITORS_GROUP = "Auditors"


class AuditorUser(BaseModel):
    id: str
    email: str
    full_name: str


class AuditorsListResponse(BaseModel):
    items: list[AuditorUser]


@router.get("/auditors", response_model=AuditorsListResponse)
async def list_auditors(
    db: AsyncSession = Depends(get_db),
):
    """Return all users with cognito group 'Auditors'."""
    users = await get_users_by_cognito_group(db, AUDITORS_GROUP)
    return AuditorsListResponse(
        items=[
            AuditorUser(id=u.id, email=u.email, full_name=u.full_name)
            for u in users
        ],
    )
