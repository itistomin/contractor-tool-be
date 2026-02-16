from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from database.models import Base


class ContractFormUpdate(Base):
    """
    Tracks the last user who updated each form part of a contract.
    One row per (contract_id, form_part); last update wins.
    """
    __tablename__ = "contract_form_updates"

    contract_id: Mapped[str] = mapped_column(
        ForeignKey("contracts.id", ondelete="CASCADE"),
        primary_key=True,
    )
    form_part: Mapped[str] = mapped_column(primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
