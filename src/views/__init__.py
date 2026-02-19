from views.authorization import router as authorization_router
from views.contractors import router as contractors_router
from views.contracts import router as contracts_router
from views.departments import router as departments_router
from views.users import router as users_router

__all__ = [
    "authorization_router",
    "contractors_router",
    "contracts_router",
    "departments_router",
    "users_router",
]
