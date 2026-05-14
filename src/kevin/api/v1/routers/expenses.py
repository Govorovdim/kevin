from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from kevin.api.v1.dependencies import get_household
from kevin.api.v1.schemas.requests.expense import ExpenseRequest
from kevin.api.v1.schemas.responses.expense import (
    ExpenseListResponse,
    ExpenseResponse,
)
from kevin.database import get_session
from kevin.exceptions import NotFoundError
from kevin.repositories.expense import ExpenseRepository
from kevin.services.expense import ExpenseService

router = APIRouter(
    prefix="/households/{household_id}/year/{year}/month/{month}/expense",
    tags=["expenses"],
    dependencies=[Depends(get_household)],
)


def get_service(session: Session = Depends(get_session)) -> ExpenseService:
    return ExpenseService(ExpenseRepository(session))


@router.get("/", response_model=ExpenseListResponse)
def list_expenses(
    household_id: int,
    year: int,
    month: int,
    service: ExpenseService = Depends(get_service),
):
    return ExpenseListResponse(
        year=year,
        month=month,
        total=service.monthly_total(household_id, year, month),
        expenses=service.list(household_id, year, month),
    )


@router.post("/", response_model=ExpenseResponse, status_code=201)
def create_expense(
    household_id: int,
    year: int,
    month: int,
    body: ExpenseRequest,
    service: ExpenseService = Depends(get_service),
):
    return service.create(household_id, year, month, body.title, body.amount)


@router.get("/{expense_id}", response_model=ExpenseResponse)
def get_expense(
    household_id: int,
    year: int,
    month: int,
    expense_id: int,
    service: ExpenseService = Depends(get_service),
):
    try:
        return service.get(expense_id, household_id, year, month)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.put("/{expense_id}", response_model=ExpenseResponse)
def update_expense(
    household_id: int,
    year: int,
    month: int,
    expense_id: int,
    body: ExpenseRequest,
    service: ExpenseService = Depends(get_service),
):
    try:
        return service.update(
            expense_id, household_id, year, month, body.title, body.amount
        )
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/{expense_id}", status_code=204)
def delete_expense(
    household_id: int,
    year: int,
    month: int,
    expense_id: int,
    service: ExpenseService = Depends(get_service),
):
    try:
        service.delete(expense_id, household_id, year, month)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
