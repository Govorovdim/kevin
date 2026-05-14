"""add year and month to assets and liabilities

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-12 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("asset", sa.Column("year", sa.Integer(), nullable=True))
    op.add_column("asset", sa.Column("month", sa.Integer(), nullable=True))
    op.execute(
        "UPDATE asset SET year = EXTRACT(YEAR FROM created_at)::INTEGER, "
        "month = EXTRACT(MONTH FROM created_at)::INTEGER"
    )
    op.alter_column("asset", "year", nullable=False)
    op.alter_column("asset", "month", nullable=False)

    op.add_column("liability", sa.Column("year", sa.Integer(), nullable=True))
    op.add_column("liability", sa.Column("month", sa.Integer(), nullable=True))
    op.execute(
        "UPDATE liability SET year = EXTRACT(YEAR FROM created_at)::INTEGER, "
        "month = EXTRACT(MONTH FROM created_at)::INTEGER"
    )
    op.alter_column("liability", "year", nullable=False)
    op.alter_column("liability", "month", nullable=False)


def downgrade() -> None:
    op.drop_column("asset", "month")
    op.drop_column("asset", "year")
    op.drop_column("liability", "month")
    op.drop_column("liability", "year")
