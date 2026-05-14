from decimal import Decimal

from kevin.repositories.asset import AssetRepository
from kevin.repositories.expense import ExpenseRepository
from kevin.repositories.income import IncomeRepository
from kevin.repositories.liability import LiabilityRepository
from kevin.schemas import MonthOverview, MonthSummary, YearOverview


class OverviewService:
    def __init__(
        self,
        expense_repo: ExpenseRepository,
        income_repo: IncomeRepository,
        asset_repo: AssetRepository,
        liability_repo: LiabilityRepository,
    ) -> None:
        self.expense_repo = expense_repo
        self.income_repo = income_repo
        self.asset_repo = asset_repo
        self.liability_repo = liability_repo

    def get_month(self, household_id: int, year: int, month: int) -> MonthOverview:
        expenses = self.expense_repo.list(household_id, year, month)
        income = self.income_repo.list(household_id, year, month)
        assets = self.asset_repo.list(household_id, year, month)
        liabilities = self.liability_repo.list(household_id, year, month)

        total_income = sum((i.amount for i in income), Decimal(0))
        total_expenses = sum((e.amount for e in expenses), Decimal(0))
        portfolio_value = sum(
            (
                (a.amount if a.amount is not None else Decimal(1))
                * (
                    a.current_price
                    if a.current_price is not None
                    else (a.bought_price if a.bought_price is not None else Decimal(0))
                )
                for a in assets
            ),
            Decimal(0),
        )
        total_debt = sum((lb.amount for lb in liabilities), Decimal(0))

        return MonthOverview(
            year=year,
            month=month,
            total_income=total_income,
            total_expenses=total_expenses,
            net_savings=total_income - total_expenses,
            income=[i.model_dump() for i in income],
            expenses=[e.model_dump() for e in expenses],
            portfolio_value=portfolio_value,
            total_debt=total_debt,
            net_worth=portfolio_value - total_debt + (total_income - total_expenses),
            assets=[a.model_dump() for a in assets],
            liabilities=[lb.model_dump() for lb in liabilities],
        )

    def get_year(self, household_id: int, year: int) -> YearOverview:
        all_expenses = self.expense_repo.list_by_year(household_id, year)
        all_income = self.income_repo.list_by_year(household_id, year)
        all_assets = self.asset_repo.list_by_year(household_id, year)
        all_liabilities = self.liability_repo.list_by_year(household_id, year)

        months_with_data = sorted(
            {e.month for e in all_expenses} | {i.month for i in all_income}
        )

        month_summaries = []
        for month in months_with_data:
            month_income = sum(
                (i.amount for i in all_income if i.month == month), Decimal(0)
            )
            month_expenses = sum(
                (e.amount for e in all_expenses if e.month == month), Decimal(0)
            )
            month_summaries.append(
                MonthSummary(
                    month=month,
                    total_income=month_income,
                    total_expenses=month_expenses,
                    net_savings=month_income - month_expenses,
                )
            )

        total_income = sum((m.total_income for m in month_summaries), Decimal(0))
        total_expenses = sum((m.total_expenses for m in month_summaries), Decimal(0))

        # Snapshot from the last month that has asset/liability data
        asset_liability_months = {a.month for a in all_assets} | {
            lb.month for lb in all_liabilities
        }
        last_month = max(asset_liability_months) if asset_liability_months else None

        last_assets = (
            [a for a in all_assets if a.month == last_month] if last_month else []
        )
        last_liabilities = (
            [lb for lb in all_liabilities if lb.month == last_month]
            if last_month
            else []
        )

        portfolio_value = sum(
            (
                (a.amount if a.amount is not None else Decimal(1))
                * (
                    a.current_price
                    if a.current_price is not None
                    else (a.bought_price if a.bought_price is not None else Decimal(0))
                )
                for a in last_assets
            ),
            Decimal(0),
        )
        total_debt = sum((lb.amount for lb in last_liabilities), Decimal(0))

        return YearOverview(
            year=year,
            total_income=total_income,
            total_expenses=total_expenses,
            net_savings=total_income - total_expenses,
            portfolio_value=portfolio_value,
            total_debt=total_debt,
            net_worth=portfolio_value - total_debt + (total_income - total_expenses),
            months=month_summaries,
        )
