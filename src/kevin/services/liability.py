from datetime import datetime, timezone
from decimal import Decimal

from kevin.exceptions import NotFoundError
from kevin.models.liability import Liability
from kevin.repositories.liability import LiabilityRepository


class LiabilityService:
    def __init__(self, repository: LiabilityRepository) -> None:
        self.repository = repository

    def list(self, household_id: int, year: int, month: int) -> list[Liability]:
        return self.repository.list(household_id, year, month)

    def get(
        self, liability_id: int, household_id: int, year: int, month: int
    ) -> Liability:
        liability = self.repository.get(liability_id, household_id)
        if not liability or liability.year != year or liability.month != month:
            raise NotFoundError(f"Liability {liability_id} not found")
        return liability

    def create(
        self, household_id: int, year: int, month: int, title: str, amount: Decimal
    ) -> Liability:
        return self.repository.create(
            Liability(
                household_id=household_id,
                year=year,
                month=month,
                title=title,
                amount=amount,
            )
        )

    def update(
        self,
        liability_id: int,
        household_id: int,
        year: int,
        month: int,
        title: str,
        amount: Decimal,
    ) -> Liability:
        liability = self.get(liability_id, household_id, year, month)
        liability.title = title
        liability.amount = amount
        liability.updated_at = datetime.now(timezone.utc)
        return self.repository.update(liability)

    def delete(
        self, liability_id: int, household_id: int, year: int, month: int
    ) -> None:
        liability = self.get(liability_id, household_id, year, month)
        self.repository.delete(liability)

    def total_debt(self, household_id: int, year: int, month: int) -> Decimal:
        return sum(
            (item.amount for item in self.list(household_id, year, month)), Decimal(0)
        )
