from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError

from kevin.api.v1.dependencies import get_auth_service, get_current_user
from kevin.api.v1.schemas.requests.auth import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
)
from kevin.api.v1.schemas.responses.auth import TokenResponse, UserResponse
from kevin.exceptions import AuthenticationError
from kevin.models.user import User
from kevin.services.auth import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=201)
def register(body: RegisterRequest, service: AuthService = Depends(get_auth_service)):
    try:
        return service.register(body.username, body.password, body.invite_token)
    except IntegrityError:
        raise HTTPException(status_code=400, detail="Username already taken")


@router.post("/login", response_model=TokenResponse)
def login(
    body: LoginRequest,
    service: AuthService = Depends(get_auth_service),
):
    try:
        tokens = service.login(body.username, body.password)
        return TokenResponse(**tokens)
    except AuthenticationError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.post("/refresh", response_model=TokenResponse)
def refresh_token(
    body: RefreshRequest,
    service: AuthService = Depends(get_auth_service),
):
    try:
        tokens = service.refresh(body.refresh_token)
        return TokenResponse(**tokens)
    except AuthenticationError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )


@router.post("/logout", status_code=204)
def logout(
    current_user: User = Depends(get_current_user),
    service: AuthService = Depends(get_auth_service),
):
    service.logout(current_user.id)


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)):
    return current_user
