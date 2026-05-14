from datetime import datetime

from pydantic import BaseModel, ConfigDict

from kevin.utils import JsonDecimal


class LiabilityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    amount: JsonDecimal
    created_at: datetime
    updated_at: datetime
