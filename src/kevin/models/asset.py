from datetime import datetime
from decimal import Decimal

from sqlalchemy import text
from sqlmodel import Field, SQLModel

from kevin.utils import utcnow


class Asset(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    household_id: int = Field(
        foreign_key="household.id", index=True, ondelete="CASCADE"
    )
    year: int = Field()
    month: int = Field()
    title: str = Field(max_length=255)
    price: Decimal = Field(default=Decimal("0"), max_digits=14, decimal_places=2)
    amount: Decimal | None = Field(default=None, max_digits=14, decimal_places=4)
    carried_forward: bool = Field(
        default=False, sa_column_kwargs={"server_default": text("false")}
    )
    previous_asset_id: int | None = Field(
        default=None, foreign_key="asset.id", index=True, ondelete="SET NULL"
    )
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)

    @property
    def quantity(self) -> Decimal:
        """Amount, treating a missing or zero amount as a single unit."""
        if self.amount is None or self.amount == 0:
            return Decimal(1)
        return self.amount

    @property
    def value(self) -> Decimal:
        return self.quantity * self.price
