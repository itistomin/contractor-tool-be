"""contract_form_updates created_at updated_at

Revision ID: 9c0d1e2f3a4b
Revises: 7b8c9d0e1f2a
Create Date: 2026-03-05

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "9c0d1e2f3a4b"
down_revision: Union[str, Sequence[str], None] = "7b8c9d0e1f2a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "contract_form_updates",
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
    )
    op.add_column(
        "contract_form_updates",
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("contract_form_updates", "updated_at")
    op.drop_column("contract_form_updates", "created_at")
