"""contract_form_updates table

Revision ID: 7b8c9d0e1f2a
Revises: 3f4a5b6c7d8e
Create Date: 2026-03-05

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "7b8c9d0e1f2a"
down_revision: Union[str, Sequence[str], None] = "3f4a5b6c7d8e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "contract_form_updates",
        sa.Column("contract_id", sa.String(), nullable=False),
        sa.Column("form_part", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(
            ["contract_id"],
            ["contracts.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("contract_id", "form_part"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("contract_form_updates")
