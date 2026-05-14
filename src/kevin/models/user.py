from datetime import datetime

from sqlmodel import Field, SQLModel

from kevin.utils import utcnow


class User(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    username: str = Field(unique=True, index=True, max_length=100)
    hashed_password: str = Field()
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
