from datetime import datetime

from sqlmodel import Field, SQLModel

from kevin.utils import utcnow


class UserHousehold(SQLModel, table=True):
    __tablename__ = "user_household"

    user_id: int = Field(foreign_key="user.id", primary_key=True, ondelete="CASCADE")
    household_id: int = Field(
        foreign_key="household.id", primary_key=True, ondelete="CASCADE"
    )
    created_at: datetime = Field(default_factory=utcnow)
