from pydantic import BaseModel

from kevin.utils import JsonDecimal


class MonthSummary(BaseModel):
    month: int
    total_income: JsonDecimal
    total_expenses: JsonDecimal
    net_savings: JsonDecimal


class MonthOverview(BaseModel):
    year: int
    month: int
    total_income: JsonDecimal
    total_expenses: JsonDecimal
    net_savings: JsonDecimal
    portfolio_value: JsonDecimal
    total_debt: JsonDecimal
    net_worth: JsonDecimal
    income: list
    expenses: list
    assets: list
    liabilities: list


class YearOverview(BaseModel):
    year: int
    total_income: JsonDecimal
    total_expenses: JsonDecimal
    net_savings: JsonDecimal
    portfolio_value: JsonDecimal
    total_debt: JsonDecimal
    net_worth: JsonDecimal
    months: list[MonthSummary]
