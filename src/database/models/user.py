from uuid import uuid4

from sqlalchemy import func
from sqlalchemy.orm import (
    Mapped, 
    mapped_column,
)

from database.models import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(primary_key=True, default=lambda: str(uuid4()))
    email: Mapped[str] = mapped_column(unique=True)
    full_name: Mapped[str] = mapped_column(unique=True)
