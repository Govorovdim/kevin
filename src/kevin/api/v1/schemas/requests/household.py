from pydantic import BaseModel, Field


class HouseholdRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class HouseholdCreateRequest(HouseholdRequest):
    currency: str = Field(
        default="USD", min_length=3, max_length=3, pattern="^[A-Z]{3}$"
    )
