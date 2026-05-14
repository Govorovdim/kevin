from datetime import datetime, timezone
from decimal import Decimal

from kevin.exceptions import NotFoundError
from kevin.models.income import Income
from kevin.repositories.income import IncomeRepository


class IncomeService:
    def __init__(self, repository: IncomeRepository) -> None:
        self.repository = repository

    def list(self, household_id: int, year: int, month: int) -> list[Income]:
        return self.repository.list(household_id, year, month)

    def get(self, income_id: int, household_id: int, year: int, month: int) -> Income:
        income = self.repository.get(income_id, household_id)
        if not income or income.year != year or income.month != month:
            raise NotFoundError(f"Income {income_id} not found")
        return income

    def create(
        self, household_id: int, year: int, month: int, title: str, amount: Decimal
    ) -> Income:
        return self.repository.create(
            Income(
                household_id=household_id,
                year=year,
                month=month,
                title=title,
                amount=amount,
            )
        )

    def update(
        self,
        income_id: int,
        household_id: int,
        year: int,
        month: int,
        title: str,
        amount: Decimal,
    ) -> Income:
        income = self.get(income_id, household_id, year, month)
        income.title = title
        income.amount = amount
        income.updated_at = datetime.now(timezone.utc)
        return self.repository.update(income)

    def delete(self, income_id: int, household_id: int, year: int, month: int) -> None:
        income = self.get(income_id, household_id, year, month)
        self.repository.delete(income)

    def monthly_total(self, household_id: int, year: int, month: int) -> Decimal:
        return sum((i.amount for i in self.list(household_id, year, month)), Decimal(0))
