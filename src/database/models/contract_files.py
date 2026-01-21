from uuid import uuid4

from sqlalchemy import ForeignKey
from sqlalchemy.orm import (
    Mapped, 
    mapped_column,
)

from database.models import Base


class ContractFiles(Base):
    __tablename__ = "contract_files"

    id: Mapped[str] = mapped_column(primary_key=True, default=lambda: str(uuid4()))
    contract_id: Mapped[str] = mapped_column(ForeignKey("contracts.id"), nullable=False)
    file_name: Mapped[str] = mapped_column()
    file_ext: Mapped[str] = mapped_column()
    file_url: Mapped[str] = mapped_column()
