from datetime import datetime, timezone
from decimal import Decimal

from kevin.exceptions import NotFoundError
from kevin.models.expense import Expense
from kevin.repositories.expense import ExpenseRepository


class ExpenseService:
    def __init__(self, repository: ExpenseRepository) -> None:
        self.repository = repository

    def list(self, household_id: int, year: int, month: int) -> list[Expense]:
        return self.repository.list(household_id, year, month)

    def get(self, expense_id: int, household_id: int, year: int, month: int) -> Expense:
        expense = self.repository.get(expense_id, household_id)
        if not expense or expense.year != year or expense.month != month:
            raise NotFoundError(f"Expense {expense_id} not found")
        return expense

    def create(
        self, household_id: int, year: int, month: int, title: str, amount: Decimal
    ) -> Expense:
        return self.repository.create(
            Expense(
                household_id=household_id,
                year=year,
                month=month,
                title=title,
                amount=amount,
            )
        )

    def update(
        self,
        expense_id: int,
        household_id: int,
        year: int,
        month: int,
        title: str,
        amount: Decimal,
    ) -> Expense:
        expense = self.get(expense_id, household_id, year, month)
        expense.title = title
        expense.amount = amount
        expense.updated_at = datetime.now(timezone.utc)
        return self.repository.update(expense)

    def delete(self, expense_id: int, household_id: int, year: int, month: int) -> None:
        expense = self.get(expense_id, household_id, year, month)
        self.repository.delete(expense)

    def monthly_total(self, household_id: int, year: int, month: int) -> Decimal:
        return sum((e.amount for e in self.list(household_id, year, month)), Decimal(0))
