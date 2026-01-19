import datetime
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

    agency_code: Mapped[str | None] = mapped_column(nullable=True)


class Agencies(Base):
    __tablename__ = "agencies"

    id: Mapped[str] = mapped_column(primary_key=True, default=lambda: str(uuid4()))
    code: Mapped[str] = mapped_column()
    name: Mapped[str] = mapped_column()
    phone: Mapped[str] = mapped_column()
    website: Mapped[str] = mapped_column()
    to_apply_url: Mapped[str] = mapped_column()
    notes: Mapped[str] = mapped_column()


class Contract(Base):
    __tablename__ = "contracts"

    id: Mapped[str] = mapped_column(primary_key=True, default=lambda: str(uuid4()))
    
    zip: Mapped[str | None] = mapped_column(nullable=True)
    city: Mapped[str | None] = mapped_column(nullable=True)
    fuel_type: Mapped[str | None] = mapped_column(nullable=True)
    
    hancock_project_id: Mapped[str | None] = mapped_column(nullable=True)
    
    date: Mapped[datetime.date | None] = mapped_column(nullable=True)
    start_at_time: Mapped[datetime.time | None] = mapped_column(nullable=True)
    end_at_time: Mapped[datetime.time | None] = mapped_column(nullable=True)
    google_meet_url: Mapped[str | None] = mapped_column(nullable=True)
    
    inspection_doc: Mapped[str | None] = mapped_column(nullable=True)
    invoice_doc: Mapped[str | None] = mapped_column(nullable=True)

    form_stage: Mapped[str] = mapped_column(default="project_id") # project_id, schedule, documents, closed
