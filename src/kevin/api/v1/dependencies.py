from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import Session

from kevin.database import get_session
from kevin.exceptions import AuthenticationError
from kevin.models.user import User
from kevin.repositories.household import HouseholdRepository
from kevin.repositories.refresh_token import RefreshTokenRepository
from kevin.repositories.user import UserRepository
from kevin.repositories.user_household import UserHouseholdRepository
from kevin.services.auth import AuthService

bearer_scheme = HTTPBearer()


def get_auth_service(session: Session = Depends(get_session)) -> AuthService:
    return AuthService(
        UserRepository(session),
        HouseholdRepository(session),
        UserHouseholdRepository(session),
        RefreshTokenRepository(session),
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    service: AuthService = Depends(get_auth_service),
) -> User:
    try:
        return service.get_user_from_token(credentials.credentials)
    except AuthenticationError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_user_household_repo(
    session: Session = Depends(get_session),
) -> UserHouseholdRepository:
    return UserHouseholdRepository(session)


def get_household(
    household_id: int,
    current_user: User = Depends(get_current_user),
    user_household_repo: UserHouseholdRepository = Depends(get_user_household_repo),
) -> int:
    membership = user_household_repo.get(current_user.id, household_id)
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access to this household is forbidden",
        )
    return household_id
