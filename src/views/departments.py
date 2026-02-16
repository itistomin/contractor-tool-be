from fastapi import APIRouter, Depends
from pydantic import BaseModel

from database.connection import get_db
from database.queries.department import get_groups_with_users
from sqlalchemy.ext.asyncio import AsyncSession


router = APIRouter(
    prefix="/departments",
    tags=["departments"],
)


class DepartmentUser(BaseModel):
    full_name: str
    email: str


class DepartmentGroup(BaseModel):
    group_name: str
    users: list[DepartmentUser]


class DepartmentsListResponse(BaseModel):
    items: list[DepartmentGroup]


@router.get("", response_model=DepartmentsListResponse)
async def list_departments(
    db: AsyncSession = Depends(get_db),
):
    """Get list of groups; each group has a list of users (group -> list of user)."""
    items = await get_groups_with_users(db)
    return DepartmentsListResponse(
        items=[
            DepartmentGroup(
                group_name=g["group_name"],
                users=[DepartmentUser(full_name=u["full_name"], email=u["email"]) for u in g["users"]],
            )
            for g in items
        ],
    )
