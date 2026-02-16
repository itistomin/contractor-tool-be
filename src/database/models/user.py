from uuid import uuid4

from sqlalchemy import ForeignKey
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
    department_id: Mapped[str | None] = mapped_column(ForeignKey("departments.id"), nullable=True)
    cognito_group: Mapped[str | None] = mapped_column(nullable=True)
