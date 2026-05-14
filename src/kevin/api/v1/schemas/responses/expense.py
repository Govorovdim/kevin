from datetime import datetime

from pydantic import BaseModel, ConfigDict

from kevin.utils import JsonDecimal


class ExpenseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    year: int
    month: int
    title: str
    amount: JsonDecimal
    created_at: datetime
    updated_at: datetime


class ExpenseListResponse(BaseModel):
    year: int
    month: int
    total: JsonDecimal
    expenses: list[ExpenseResponse]
