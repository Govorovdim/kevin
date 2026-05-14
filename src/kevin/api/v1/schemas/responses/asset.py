from datetime import datetime

from pydantic import BaseModel, ConfigDict

from kevin.utils import JsonDecimal


class AssetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    ticker: str | None
    amount: JsonDecimal | None
    bought_price: JsonDecimal | None
    current_price: JsonDecimal | None
    created_at: datetime
    updated_at: datetime
