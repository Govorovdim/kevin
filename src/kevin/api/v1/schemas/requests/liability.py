from decimal import Decimal

from pydantic import BaseModel, Field


class LiabilityRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
