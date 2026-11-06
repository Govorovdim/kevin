"""Add asset carry-forward fields.

Revision ID: 0008
Revises: 0007
Create Date: 2026-06-26 00:00:00.000000
"""

import sqlalchemy as sa
from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "asset",
        sa.Column(
            "carried_forward",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column("asset", sa.Column("previous_asset_id", sa.Integer(), nullable=True))
    op.create_index("ix_asset_previous_asset_id", "asset", ["previous_asset_id"])
    op.create_foreign_key(
        "fk_asset_previous_asset_id_asset",
        "asset",
        "asset",
        ["previous_asset_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_asset_previous_asset_id_asset", "asset", type_="foreignkey")
    op.drop_index("ix_asset_previous_asset_id", "asset")
    op.drop_column("asset", "previous_asset_id")
    op.drop_column("asset", "carried_forward")
