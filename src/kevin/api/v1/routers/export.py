from io import BytesIO
from typing import Optional

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    Request,
    UploadFile,
    status,
)
from fastapi.responses import StreamingResponse
from sqlmodel import Session

from kevin.api.v1.dependencies import get_current_user
from kevin.database import get_session
from kevin.exceptions import AuthenticationError
from kevin.models.user import User
from kevin.repositories.asset import AssetRepository
from kevin.repositories.expense import ExpenseRepository
from kevin.repositories.household import HouseholdRepository
from kevin.repositories.income import IncomeRepository
from kevin.repositories.liability import LiabilityRepository
from kevin.repositories.user import UserRepository
from kevin.repositories.user_household import UserHouseholdRepository
from kevin.services.auth import AuthService
from kevin.services.export import ExportService
from kevin.services.import_data import ImportService

router = APIRouter(
    prefix="/households/{household_id}",
    tags=["export"],
)

MAX_IMPORT_SIZE = 10 * 1024 * 1024  # 10 MB


def _resolve_export_user(
    request: Request,
    token: Optional[str],
    session: Session,
) -> User:
    """Authenticate the export request via Bearer header or query-param token."""
    auth_service = AuthService(
        UserRepository(session),
        HouseholdRepository(session),
        UserHouseholdRepository(session),
    )

    # 1. Try Authorization header first
    auth_header = request.headers.get("authorization", "")
    if auth_header.lower().startswith("bearer "):
        bearer_token = auth_header[7:]
        try:
            return auth_service.get_user_from_token(bearer_token)
        except AuthenticationError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
            )

    # 2. Fall back to query-param token (legacy / direct browser navigation)
    if token:
        try:
            return auth_service.get_user_from_token(token)
        except AuthenticationError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
            )

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required",
    )


@router.get("/export")
def export_household(
    household_id: int,
    request: Request,
    start_year: int = Query(...),
    start_month: int = Query(..., ge=1, le=12),
    end_year: int = Query(...),
    end_month: int = Query(..., ge=1, le=12),
    token: Optional[str] = Query(None),
    session: Session = Depends(get_session),
):
    user = _resolve_export_user(request, token, session)

    membership = UserHouseholdRepository(session).get(user.id, household_id)
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access to this household is forbidden",
        )

    household = HouseholdRepository(session).get(household_id)
    currency = household.currency if household else "USD"

    service = ExportService(
        ExpenseRepository(session),
        IncomeRepository(session),
        AssetRepository(session),
        LiabilityRepository(session),
    )
    content = service.export_household(
        household_id,
        start_year,
        start_month,
        end_year,
        end_month,
        currency=currency,
    )
    filename = (
        f"household_export_{start_year}-{start_month:02d}"
        f"_{end_year}-{end_month:02d}.xlsx"
    )
    return StreamingResponse(
        BytesIO(content),
        media_type=(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ),
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/import")
async def import_household(
    household_id: int,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    # Check membership
    membership = UserHouseholdRepository(session).get(current_user.id, household_id)
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access to this household is forbidden",
        )

    file_bytes = await file.read()
    if len(file_bytes) > MAX_IMPORT_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File too large. Maximum size is 10 MB.",
        )

    service = ImportService(
        ExpenseRepository(session),
        IncomeRepository(session),
        AssetRepository(session),
        LiabilityRepository(session),
    )
    try:
        counts = service.import_household(household_id, file_bytes)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to parse the uploaded file. Please check the format and try again.",
        )

    return {
        "message": "Import successful",
        "imported": counts,
    }
