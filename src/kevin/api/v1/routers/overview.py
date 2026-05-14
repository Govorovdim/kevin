from fastapi import APIRouter, Depends
from sqlmodel import Session

from kevin.api.v1.dependencies import get_household
from kevin.api.v1.schemas.responses.overview import (
    MonthOverviewResponse,
    YearOverviewResponse,
)
from kevin.database import get_session
from kevin.repositories.asset import AssetRepository
from kevin.repositories.expense import ExpenseRepository
from kevin.repositories.income import IncomeRepository
from kevin.repositories.liability import LiabilityRepository
from kevin.services.overview import OverviewService

router = APIRouter(
    prefix="/households/{household_id}",
    tags=["overview"],
    dependencies=[Depends(get_household)],
)


def get_service(session: Session = Depends(get_session)) -> OverviewService:
    return OverviewService(
        ExpenseRepository(session),
        IncomeRepository(session),
        AssetRepository(session),
        LiabilityRepository(session),
    )


@router.get("/year/{year}/month/{month}", response_model=MonthOverviewResponse)
def get_month_overview(
    household_id: int,
    year: int,
    month: int,
    service: OverviewService = Depends(get_service),
):
    return service.get_month(household_id, year, month)


@router.get("/year/{year}", response_model=YearOverviewResponse)
def get_year_overview(
    household_id: int,
    year: int,
    service: OverviewService = Depends(get_service),
):
    return service.get_year(household_id, year)
