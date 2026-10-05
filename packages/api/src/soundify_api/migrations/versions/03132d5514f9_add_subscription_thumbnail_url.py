"""Add subscription thumbnail_url

Revision ID: 03132d5514f9
Revises: b36ae7fb398c
Create Date: 2026-01-30 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "03132d5514f9"
down_revision: str | Sequence[str] | None = "b36ae7fb398c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "subscriptions",
        sa.Column("thumbnail_url", sa.VARCHAR(length=2048), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("subscriptions", "thumbnail_url")
