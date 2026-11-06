from datetime import datetime

from pydantic import BaseModel, ConfigDict

from kevin.utils import JsonDecimal


class AssetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    price: JsonDecimal
    amount: JsonDecimal | None
    carried_forward: bool
    previous_asset_id: int | None
    created_at: datetime
    updated_at: datetime
