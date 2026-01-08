from uuid import uuid4

from sqlalchemy import func
from sqlalchemy.orm import (
    Mapped, 
    mapped_column,
)

from database.models import Base


class ZipProfiles(Base):
    __tablename__ = "zip_profiles"

    id: Mapped[str] = mapped_column(primary_key=True, default=lambda: str(uuid4()))
    zip_code: Mapped[str] = mapped_column()
    city: Mapped[str] = mapped_column()
    fuel_type: Mapped[str] = mapped_column()
    sponsored: Mapped[str] = mapped_column()
    utility_type: Mapped[str] = mapped_column()
    has_utility: Mapped[bool] = mapped_column(default=False)

    proceed_reason: Mapped[str] = mapped_column()
    is_dec: Mapped[bool] = mapped_column(default=False)
    electrification_candidate: Mapped[bool] = mapped_column(default=False)

    # FK to agencies table
