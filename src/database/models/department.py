from uuid import uuid4

from sqlalchemy.orm import (
    Mapped, 
    mapped_column,
)

from database.models import Base


class Department(Base):
    __tablename__ = "departments"

    id: Mapped[str] = mapped_column(primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column()
    role: Mapped[str] = mapped_column()
