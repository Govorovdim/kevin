"""Simplify assets to a single price and optional amount.

Revision ID: 0009
Revises: 0008
Create Date: 2026-11-06 00:00:00.000000
"""

import sqlalchemy as sa
from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "asset",
        sa.Column("price", sa.Numeric(precision=14, scale=2), nullable=True),
    )
    op.execute("UPDATE asset SET price = COALESCE(current_price, bought_price, 0)")
    op.alter_column("asset", "price", nullable=False)

    op.drop_column("asset", "ticker")
    op.drop_column("asset", "bought_price")
    op.drop_column("asset", "current_price")


def downgrade() -> None:
    op.add_column("asset", sa.Column("ticker", sa.String(length=20), nullable=True))
    op.add_column(
        "asset",
        sa.Column("bought_price", sa.Numeric(precision=14, scale=2), nullable=True),
    )
    op.add_column(
        "asset",
        sa.Column("current_price", sa.Numeric(precision=14, scale=2), nullable=True),
    )
    op.execute("UPDATE asset SET bought_price = price, current_price = price")
    op.drop_column("asset", "price")
