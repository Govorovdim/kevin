"""add invite_token to household

Revision ID: 0003
Revises: 0002
Create Date: 2026-05-13 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("household", sa.Column("invite_token", sa.String(), nullable=True))
    op.create_index(
        op.f("ix_household_invite_token"), "household", ["invite_token"], unique=True
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_household_invite_token"), table_name="household")
    op.drop_column("household", "invite_token")
