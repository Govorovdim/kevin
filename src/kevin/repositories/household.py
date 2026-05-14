from sqlmodel import Session, select

from kevin.models.household import Household
from kevin.models.user_household import UserHousehold
from kevin.utils import utcnow


class HouseholdRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_by_user(self, user_id: int) -> list[Household]:
        return list(
            self.session.exec(
                select(Household)
                .join(UserHousehold, Household.id == UserHousehold.household_id)
                .where(UserHousehold.user_id == user_id)
            ).all()
        )

    def get(self, household_id: int) -> Household | None:
        return self.session.get(Household, household_id)

    def get_by_invite_token(self, token: str) -> Household | None:
        return self.session.exec(
            select(Household).where(Household.invite_token == token)
        ).first()

    def create(self, household: Household) -> Household:
        self.session.add(household)
        self.session.commit()
        self.session.refresh(household)
        return household

    def update(self, household: Household) -> Household:
        self.session.add(household)
        household.updated_at = utcnow()
        self.session.commit()
        self.session.refresh(household)
        return household

    def delete(self, household: Household) -> None:
        self.session.delete(household)
        self.session.commit()
