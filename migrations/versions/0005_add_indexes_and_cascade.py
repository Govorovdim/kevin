"""Add composite indexes and ON DELETE CASCADE.

Revision ID: 0005
Revises: 0004
Create Date: 2026-05-13 00:00:00.000000
"""

from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Composite indexes for primary query pattern
    op.create_index(
        "ix_income_household_year_month", "income", ["household_id", "year", "month"]
    )
    op.create_index(
        "ix_expense_household_year_month", "expense", ["household_id", "year", "month"]
    )
    op.create_index(
        "ix_asset_household_year_month", "asset", ["household_id", "year", "month"]
    )
    op.create_index(
        "ix_liability_household_year_month",
        "liability",
        ["household_id", "year", "month"],
    )

    # Add ON DELETE CASCADE to foreign keys
    # Income
    op.drop_constraint("income_household_id_fkey", "income", type_="foreignkey")
    op.create_foreign_key(
        "income_household_id_fkey",
        "income",
        "household",
        ["household_id"],
        ["id"],
        ondelete="CASCADE",
    )
    # Expense
    op.drop_constraint("expense_household_id_fkey", "expense", type_="foreignkey")
    op.create_foreign_key(
        "expense_household_id_fkey",
        "expense",
        "household",
        ["household_id"],
        ["id"],
        ondelete="CASCADE",
    )
    # Asset
    op.drop_constraint("asset_household_id_fkey", "asset", type_="foreignkey")
    op.create_foreign_key(
        "asset_household_id_fkey",
        "asset",
        "household",
        ["household_id"],
        ["id"],
        ondelete="CASCADE",
    )
    # Liability
    op.drop_constraint("liability_household_id_fkey", "liability", type_="foreignkey")
    op.create_foreign_key(
        "liability_household_id_fkey",
        "liability",
        "household",
        ["household_id"],
        ["id"],
        ondelete="CASCADE",
    )
    # UserHousehold
    op.drop_constraint(
        "user_household_user_id_fkey", "user_household", type_="foreignkey"
    )
    op.create_foreign_key(
        "user_household_user_id_fkey",
        "user_household",
        "user",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.drop_constraint(
        "user_household_household_id_fkey", "user_household", type_="foreignkey"
    )
    op.create_foreign_key(
        "user_household_household_id_fkey",
        "user_household",
        "household",
        ["household_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    # Remove composite indexes
    op.drop_index("ix_income_household_year_month", "income")
    op.drop_index("ix_expense_household_year_month", "expense")
    op.drop_index("ix_asset_household_year_month", "asset")
    op.drop_index("ix_liability_household_year_month", "liability")

    # Revert CASCADE foreign keys back to default
    op.drop_constraint("income_household_id_fkey", "income", type_="foreignkey")
    op.create_foreign_key(
        "income_household_id_fkey", "income", "household", ["household_id"], ["id"]
    )
    op.drop_constraint("expense_household_id_fkey", "expense", type_="foreignkey")
    op.create_foreign_key(
        "expense_household_id_fkey", "expense", "household", ["household_id"], ["id"]
    )
    op.drop_constraint("asset_household_id_fkey", "asset", type_="foreignkey")
    op.create_foreign_key(
        "asset_household_id_fkey", "asset", "household", ["household_id"], ["id"]
    )
    op.drop_constraint("liability_household_id_fkey", "liability", type_="foreignkey")
    op.create_foreign_key(
        "liability_household_id_fkey",
        "liability",
        "household",
        ["household_id"],
        ["id"],
    )
    op.drop_constraint(
        "user_household_user_id_fkey", "user_household", type_="foreignkey"
    )
    op.create_foreign_key(
        "user_household_user_id_fkey", "user_household", "user", ["user_id"], ["id"]
    )
    op.drop_constraint(
        "user_household_household_id_fkey", "user_household", type_="foreignkey"
    )
    op.create_foreign_key(
        "user_household_household_id_fkey",
        "user_household",
        "household",
        ["household_id"],
        ["id"],
    )
