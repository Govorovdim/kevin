from pydantic import BaseModel

from kevin.api.v1.schemas.responses.asset import AssetResponse
from kevin.api.v1.schemas.responses.expense import ExpenseResponse
from kevin.api.v1.schemas.responses.income import IncomeResponse
from kevin.api.v1.schemas.responses.liability import LiabilityResponse
from kevin.utils import JsonDecimal


class MonthSummaryResponse(BaseModel):
    month: int
    total_income: JsonDecimal
    total_expenses: JsonDecimal
    net_savings: JsonDecimal


class MonthOverviewResponse(BaseModel):
    year: int
    month: int
    total_income: JsonDecimal
    total_expenses: JsonDecimal
    net_savings: JsonDecimal
    income: list[IncomeResponse]
    expenses: list[ExpenseResponse]
    portfolio_value: JsonDecimal
    total_debt: JsonDecimal
    net_worth: JsonDecimal
    assets: list[AssetResponse]
    liabilities: list[LiabilityResponse]


class YearOverviewResponse(BaseModel):
    year: int
    total_income: JsonDecimal
    total_expenses: JsonDecimal
    net_savings: JsonDecimal
    portfolio_value: JsonDecimal
    total_debt: JsonDecimal
    net_worth: JsonDecimal
    months: list[MonthSummaryResponse]
