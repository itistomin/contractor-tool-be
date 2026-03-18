"""contract multifamily values

Revision ID: 7c2f1b9e4a01
Revises: d85f99a725b4
Create Date: 2026-03-18

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "7c2f1b9e4a01"
down_revision: Union[str, Sequence[str], None] = "d85f99a725b4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("contracts", sa.Column("multifamily_values", sa.JSON(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("contracts", "multifamily_values")

