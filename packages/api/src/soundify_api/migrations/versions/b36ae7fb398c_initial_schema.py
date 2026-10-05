"""Initial schema

Revision ID: b36ae7fb398c
Revises:
Create Date: 2026-01-30 01:08:16.602862

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b36ae7fb398c"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "subscriptions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("type", sa.VARCHAR(), nullable=False),
        sa.Column("url", sa.VARCHAR(), nullable=False),
        sa.Column("name", sa.VARCHAR(length=200), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("max_items", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("last_synced_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_subscriptions_type"), "subscriptions", ["type"], unique=False
    )
    op.create_index(op.f("ix_subscriptions_url"), "subscriptions", ["url"], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_subscriptions_url"), table_name="subscriptions")
    op.drop_index(op.f("ix_subscriptions_type"), table_name="subscriptions")
    op.drop_table("subscriptions")
