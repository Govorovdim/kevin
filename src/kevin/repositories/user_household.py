from sqlalchemy import delete as sa_delete
from sqlalchemy import func
from sqlmodel import Session, select

from kevin.models.user_household import UserHousehold


class UserHouseholdRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, user_id: int, household_id: int) -> UserHousehold:
        membership = UserHousehold(user_id=user_id, household_id=household_id)
        self.session.add(membership)
        self.session.commit()
        self.session.refresh(membership)
        return membership

    def get(self, user_id: int, household_id: int) -> UserHousehold | None:
        return self.session.get(UserHousehold, (user_id, household_id))

    def exists(self, user_id: int, household_id: int) -> bool:
        return self.get(user_id, household_id) is not None

    def count_by_household(self, household_id: int) -> int:
        result = self.session.exec(
            select(func.count()).where(UserHousehold.household_id == household_id)
        )
        return result.one()

    def remove(self, user_id: int, household_id: int) -> None:
        membership = self.get(user_id, household_id)
        if membership:
            self.session.delete(membership)
            self.session.commit()

    def delete_by_household(self, household_id: int) -> None:
        self.session.execute(
            sa_delete(UserHousehold).where(UserHousehold.household_id == household_id)
        )
        self.session.commit()
