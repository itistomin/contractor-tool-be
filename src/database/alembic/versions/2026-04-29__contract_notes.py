"""contract notes

Revision ID: 7e0a3d1c4b2f
Revises: 2f7a6c1b9d3e
Create Date: 2026-04-29

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "7e0a3d1c4b2f"
down_revision: Union[str, Sequence[str], None] = "2f7a6c1b9d3e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("contracts", sa.Column("notes", sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("contracts", "notes")

