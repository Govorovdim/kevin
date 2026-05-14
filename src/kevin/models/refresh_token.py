from datetime import datetime

from sqlmodel import Field, SQLModel

from kevin.utils import utcnow


class RefreshToken(SQLModel, table=True):
    __tablename__ = "refresh_token"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True, ondelete="CASCADE")
    token_hash: str = Field(index=True)
    expires_at: datetime = Field()
    revoked: bool = Field(default=False)
    created_at: datetime = Field(default_factory=utcnow)
