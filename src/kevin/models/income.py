from datetime import datetime
from decimal import Decimal

from sqlmodel import Field, SQLModel

from kevin.utils import utcnow


class Income(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    household_id: int = Field(
        foreign_key="household.id", index=True, ondelete="CASCADE"
    )
    year: int = Field()
    month: int = Field()
    title: str = Field(max_length=255)
    amount: Decimal = Field(max_digits=14, decimal_places=2)
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
