from datetime import datetime

from pydantic import BaseModel, ConfigDict


class HouseholdResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    currency: str
    invite_token: str | None
    created_at: datetime
    updated_at: datetime
    member_count: int = 0
