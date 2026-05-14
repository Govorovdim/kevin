from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from kevin.api.v1.dependencies import get_household
from kevin.api.v1.schemas.requests.asset import AssetRequest, AssetUpdatePriceRequest
from kevin.api.v1.schemas.responses.asset import AssetResponse
from kevin.database import get_session
from kevin.exceptions import NotFoundError
from kevin.repositories.asset import AssetRepository
from kevin.services.asset import AssetService

router = APIRouter(
    prefix="/households/{household_id}/year/{year}/month/{month}/asset",
    tags=["assets"],
    dependencies=[Depends(get_household)],
)


def get_service(session: Session = Depends(get_session)) -> AssetService:
    return AssetService(AssetRepository(session))


@router.get("/", response_model=list[AssetResponse])
def list_assets(
    household_id: int,
    year: int,
    month: int,
    service: AssetService = Depends(get_service),
):
    return service.list(household_id, year, month)


@router.post("/", response_model=AssetResponse, status_code=201)
def create_asset(
    household_id: int,
    year: int,
    month: int,
    body: AssetRequest,
    service: AssetService = Depends(get_service),
):
    return service.create(
        household_id,
        year,
        month,
        body.title,
        body.ticker,
        body.amount,
        body.bought_price,
        body.current_price,
    )


@router.get("/{asset_id}", response_model=AssetResponse)
def get_asset(
    household_id: int,
    year: int,
    month: int,
    asset_id: int,
    service: AssetService = Depends(get_service),
):
    try:
        return service.get(asset_id, household_id, year, month)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.put("/{asset_id}", response_model=AssetResponse)
def update_asset(
    household_id: int,
    year: int,
    month: int,
    asset_id: int,
    body: AssetRequest,
    service: AssetService = Depends(get_service),
):
    try:
        return service.update(
            asset_id,
            household_id,
            year,
            month,
            body.title,
            body.ticker,
            body.amount,
            body.bought_price,
            body.current_price,
        )
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.patch("/{asset_id}/price", response_model=AssetResponse)
def update_asset_price(
    household_id: int,
    year: int,
    month: int,
    asset_id: int,
    body: AssetUpdatePriceRequest,
    service: AssetService = Depends(get_service),
):
    try:
        return service.update_price(
            asset_id, household_id, year, month, body.current_price
        )
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/{asset_id}", status_code=204)
def delete_asset(
    household_id: int,
    year: int,
    month: int,
    asset_id: int,
    service: AssetService = Depends(get_service),
):
    try:
        service.delete(asset_id, household_id, year, month)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
