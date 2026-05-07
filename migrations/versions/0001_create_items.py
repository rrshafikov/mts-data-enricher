"""create items table

Revision ID: 0001
Revises:
Create Date: 2026-05-07

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("key", sa.String(length=255), nullable=False),
        sa.Column("additional_info", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
    )
    op.create_index("ix_items_status", "items", ["status"])


def downgrade() -> None:
    op.drop_index("ix_items_status", table_name="items")
    op.drop_table("items")
