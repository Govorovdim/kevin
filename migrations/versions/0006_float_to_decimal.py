"""Convert monetary float columns to numeric (decimal).

Revision ID: 0006
Revises: 0005
Create Date: 2026-05-14 00:00:00.000000
"""

import sqlalchemy as sa
from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Income
    op.alter_column(
        "income",
        "amount",
        type_=sa.Numeric(precision=14, scale=2),
        existing_type=sa.Float(),
        existing_nullable=False,
    )
    # Expense
    op.alter_column(
        "expense",
        "amount",
        type_=sa.Numeric(precision=14, scale=2),
        existing_type=sa.Float(),
        existing_nullable=False,
    )
    # Liability
    op.alter_column(
        "liability",
        "amount",
        type_=sa.Numeric(precision=14, scale=2),
        existing_type=sa.Float(),
        existing_nullable=False,
    )
    # Asset
    op.alter_column(
        "asset",
        "amount",
        type_=sa.Numeric(precision=14, scale=4),
        existing_type=sa.Float(),
        existing_nullable=True,
    )
    op.alter_column(
        "asset",
        "bought_price",
        type_=sa.Numeric(precision=14, scale=2),
        existing_type=sa.Float(),
        existing_nullable=True,
    )
    op.alter_column(
        "asset",
        "current_price",
        type_=sa.Numeric(precision=14, scale=2),
        existing_type=sa.Float(),
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "income",
        "amount",
        type_=sa.Float(),
        existing_type=sa.Numeric(precision=14, scale=2),
    )
    op.alter_column(
        "expense",
        "amount",
        type_=sa.Float(),
        existing_type=sa.Numeric(precision=14, scale=2),
    )
    op.alter_column(
        "liability",
        "amount",
        type_=sa.Float(),
        existing_type=sa.Numeric(precision=14, scale=2),
    )
    op.alter_column(
        "asset",
        "amount",
        type_=sa.Float(),
        existing_type=sa.Numeric(precision=14, scale=4),
    )
    op.alter_column(
        "asset",
        "bought_price",
        type_=sa.Float(),
        existing_type=sa.Numeric(precision=14, scale=2),
    )
    op.alter_column(
        "asset",
        "current_price",
        type_=sa.Float(),
        existing_type=sa.Numeric(precision=14, scale=2),
    )
