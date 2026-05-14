from datetime import datetime

from sqlmodel import Field, SQLModel

from kevin.utils import utcnow


class Household(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(max_length=255)
    invite_token: str | None = Field(default=None, index=True, unique=True)
    currency: str = Field(default="USD", max_length=3)
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
