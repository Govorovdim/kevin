from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from kevin.api.v1.dependencies import get_household
from kevin.api.v1.schemas.requests.liability import LiabilityRequest
from kevin.api.v1.schemas.responses.liability import LiabilityResponse
from kevin.database import get_session
from kevin.exceptions import NotFoundError
from kevin.repositories.liability import LiabilityRepository
from kevin.services.liability import LiabilityService

router = APIRouter(
    prefix="/households/{household_id}/year/{year}/month/{month}/liability",
    tags=["liabilities"],
    dependencies=[Depends(get_household)],
)


def get_service(session: Session = Depends(get_session)) -> LiabilityService:
    return LiabilityService(LiabilityRepository(session))


@router.get("/", response_model=list[LiabilityResponse])
def list_liabilities(
    household_id: int,
    year: int,
    month: int,
    service: LiabilityService = Depends(get_service),
):
    return service.list(household_id, year, month)


@router.post("/", response_model=LiabilityResponse, status_code=201)
def create_liability(
    household_id: int,
    year: int,
    month: int,
    body: LiabilityRequest,
    service: LiabilityService = Depends(get_service),
):
    return service.create(household_id, year, month, body.title, body.amount)


@router.get("/{liability_id}", response_model=LiabilityResponse)
def get_liability(
    household_id: int,
    year: int,
    month: int,
    liability_id: int,
    service: LiabilityService = Depends(get_service),
):
    try:
        return service.get(liability_id, household_id, year, month)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.put("/{liability_id}", response_model=LiabilityResponse)
def update_liability(
    household_id: int,
    year: int,
    month: int,
    liability_id: int,
    body: LiabilityRequest,
    service: LiabilityService = Depends(get_service),
):
    try:
        return service.update(
            liability_id, household_id, year, month, body.title, body.amount
        )
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/{liability_id}", status_code=204)
def delete_liability(
    household_id: int,
    year: int,
    month: int,
    liability_id: int,
    service: LiabilityService = Depends(get_service),
):
    try:
        service.delete(liability_id, household_id, year, month)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
