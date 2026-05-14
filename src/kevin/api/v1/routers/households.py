from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from kevin.api.v1.dependencies import (
    get_current_user,
    get_household,
    get_user_household_repo,
)
from kevin.api.v1.schemas.requests.household import (
    HouseholdCreateRequest,
    HouseholdRequest,
)
from kevin.api.v1.schemas.responses.household import HouseholdResponse
from kevin.database import get_session
from kevin.exceptions import NotFoundError
from kevin.models.user import User
from kevin.repositories.household import HouseholdRepository
from kevin.repositories.user_household import UserHouseholdRepository
from kevin.services.household import HouseholdService

router = APIRouter(prefix="/households", tags=["households"])


def get_service(session: Session = Depends(get_session)) -> HouseholdService:
    return HouseholdService(
        HouseholdRepository(session),
        UserHouseholdRepository(session),
    )


@router.get("/", response_model=list[HouseholdResponse])
def list_households(
    current_user: User = Depends(get_current_user),
    service: HouseholdService = Depends(get_service),
    user_household_repo: UserHouseholdRepository = Depends(get_user_household_repo),
):
    households = service.list(current_user.id)
    return [
        HouseholdResponse(
            id=h.id,
            name=h.name,
            currency=h.currency,
            invite_token=h.invite_token,
            created_at=h.created_at,
            updated_at=h.updated_at,
            member_count=user_household_repo.count_by_household(h.id),
        )
        for h in households
    ]


@router.post("/", response_model=HouseholdResponse, status_code=201)
def create_household(
    body: HouseholdCreateRequest,
    current_user: User = Depends(get_current_user),
    service: HouseholdService = Depends(get_service),
):
    return service.create(current_user.id, body.name, body.currency)


@router.post(
    "/{household_id}/invite",
    response_model=HouseholdResponse,
    dependencies=[Depends(get_household)],
)
def generate_invite(
    household_id: int,
    service: HouseholdService = Depends(get_service),
):
    """Generate or regenerate an invite token for this household."""
    try:
        return service.generate_invite(household_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/join/{token}", response_model=HouseholdResponse)
def get_household_by_invite(
    token: str,
    service: HouseholdService = Depends(get_service),
):
    """Public endpoint — look up a household by its invite token (no auth required)."""
    try:
        return service.get_by_invite_token(token)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/join/{token}", response_model=HouseholdResponse)
def join_household_by_invite(
    token: str,
    current_user: User = Depends(get_current_user),
    service: HouseholdService = Depends(get_service),
):
    """Authenticated endpoint — join a household via invite token."""
    try:
        return service.join_by_invite(current_user.id, token)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get(
    "/{household_id}",
    response_model=HouseholdResponse,
    dependencies=[Depends(get_household)],
)
def get_household_by_id(
    household_id: int,
    service: HouseholdService = Depends(get_service),
):
    try:
        return service.get(household_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.put(
    "/{household_id}",
    response_model=HouseholdResponse,
    dependencies=[Depends(get_household)],
)
def update_household(
    household_id: int,
    body: HouseholdRequest,
    service: HouseholdService = Depends(get_service),
):
    try:
        return service.update(household_id, body.name)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete(
    "/{household_id}",
    status_code=204,
    dependencies=[Depends(get_household)],
)
def delete_household(
    household_id: int,
    service: HouseholdService = Depends(get_service),
    user_household_repo: UserHouseholdRepository = Depends(get_user_household_repo),
):
    if user_household_repo.count_by_household(household_id) > 1:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete a household with other members. Leave it first.",
        )
    try:
        service.delete(household_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete(
    "/{household_id}/leave", status_code=204, dependencies=[Depends(get_household)]
)
def leave_household(
    household_id: int,
    current_user: User = Depends(get_current_user),
    service: HouseholdService = Depends(get_service),
):
    try:
        service.leave(current_user.id, household_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
