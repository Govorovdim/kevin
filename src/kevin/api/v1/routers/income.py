from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from kevin.api.v1.dependencies import get_household
from kevin.api.v1.schemas.requests.income import IncomeRequest
from kevin.api.v1.schemas.responses.income import IncomeListResponse, IncomeResponse
from kevin.database import get_session
from kevin.exceptions import NotFoundError
from kevin.repositories.income import IncomeRepository
from kevin.services.income import IncomeService

router = APIRouter(
    prefix="/households/{household_id}/year/{year}/month/{month}/income",
    tags=["income"],
    dependencies=[Depends(get_household)],
)


def get_service(session: Session = Depends(get_session)) -> IncomeService:
    return IncomeService(IncomeRepository(session))


@router.get("/", response_model=IncomeListResponse)
def list_income(
    household_id: int,
    year: int,
    month: int,
    service: IncomeService = Depends(get_service),
):
    return IncomeListResponse(
        year=year,
        month=month,
        total=service.monthly_total(household_id, year, month),
        income=service.list(household_id, year, month),
    )


@router.post("/", response_model=IncomeResponse, status_code=201)
def create_income(
    household_id: int,
    year: int,
    month: int,
    body: IncomeRequest,
    service: IncomeService = Depends(get_service),
):
    return service.create(household_id, year, month, body.title, body.amount)


@router.get("/{income_id}", response_model=IncomeResponse)
def get_income(
    household_id: int,
    year: int,
    month: int,
    income_id: int,
    service: IncomeService = Depends(get_service),
):
    try:
        return service.get(income_id, household_id, year, month)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.put("/{income_id}", response_model=IncomeResponse)
def update_income(
    household_id: int,
    year: int,
    month: int,
    income_id: int,
    body: IncomeRequest,
    service: IncomeService = Depends(get_service),
):
    try:
        return service.update(
            income_id, household_id, year, month, body.title, body.amount
        )
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/{income_id}", status_code=204)
def delete_income(
    household_id: int,
    year: int,
    month: int,
    income_id: int,
    service: IncomeService = Depends(get_service),
):
    try:
        service.delete(income_id, household_id, year, month)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
