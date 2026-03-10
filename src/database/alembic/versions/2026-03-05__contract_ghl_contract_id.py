"""contract ghl_contract_id and client_email

Revision ID: 3f4a5b6c7d8e
Revises: a7b8c9d0e1f2
Create Date: 2026-03-05

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "3f4a5b6c7d8e"
down_revision: Union[str, Sequence[str], None] = "a7b8c9d0e1f2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "contracts",
        sa.Column("ghl_contract_id", sa.String(), nullable=True),
    )
    op.add_column(
        "contracts",
        sa.Column("client_email", sa.String(), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("contracts", "client_email")
    op.drop_column("contracts", "ghl_contract_id")
