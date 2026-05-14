from decimal import Decimal

from pydantic import BaseModel, Field


class AssetRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    ticker: str | None = Field(default=None, max_length=20)
    amount: Decimal | None = Field(default=None, max_digits=14, decimal_places=4)
    bought_price: Decimal | None = Field(default=None, max_digits=14, decimal_places=2)
    current_price: Decimal | None = Field(default=None, max_digits=14, decimal_places=2)


class AssetUpdatePriceRequest(BaseModel):
    current_price: Decimal = Field(max_digits=14, decimal_places=2)
