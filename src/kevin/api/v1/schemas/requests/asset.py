from decimal import Decimal

from pydantic import BaseModel, Field


class AssetRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    price: Decimal = Field(default=Decimal("0"), max_digits=14, decimal_places=2)
    amount: Decimal | None = Field(default=None, max_digits=14, decimal_places=4)
    carried_forward: bool = False


class AssetUpdateRequest(AssetRequest):
    # Omit the field to leave the current value untouched.
    carried_forward: bool | None = None
