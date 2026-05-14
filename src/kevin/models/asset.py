from datetime import datetime
from decimal import Decimal

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
    ticker: str | None = Field(default=None, max_length=20)
    amount: Decimal | None = Field(default=None, max_digits=14, decimal_places=4)
    bought_price: Decimal | None = Field(default=None, max_digits=14, decimal_places=2)
    current_price: Decimal | None = Field(default=None, max_digits=14, decimal_places=2)
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
