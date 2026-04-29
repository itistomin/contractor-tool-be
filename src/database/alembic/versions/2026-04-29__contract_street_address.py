"""contract street address

Revision ID: 2f7a6c1b9d3e
Revises: 7c2f1b9e4a01
Create Date: 2026-04-29

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "2f7a6c1b9d3e"
down_revision: Union[str, Sequence[str], None] = "7c2f1b9e4a01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("contracts", sa.Column("street_address", sa.String(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("contracts", "street_address")

