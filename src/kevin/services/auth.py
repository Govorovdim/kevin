import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
from jose import JWTError, jwt

from kevin.exceptions import AuthenticationError
from kevin.models.household import Household
from kevin.models.refresh_token import RefreshToken
from kevin.models.user import User
from kevin.repositories.household import HouseholdRepository
from kevin.repositories.refresh_token import RefreshTokenRepository
from kevin.repositories.user import UserRepository
from kevin.repositories.user_household import UserHouseholdRepository
from kevin.settings import settings


class AuthService:
    def __init__(
        self,
        user_repo: UserRepository,
        household_repo: HouseholdRepository,
        user_household_repo: UserHouseholdRepository,
        refresh_token_repo: RefreshTokenRepository | None = None,
    ) -> None:
        self.user_repo = user_repo
        self.household_repo = household_repo
        self.user_household_repo = user_household_repo
        self.refresh_token_repo = refresh_token_repo

    def register(
        self, username: str, password: str, invite_token: str | None = None
    ) -> User:
        if len(password) > 128:
            raise AuthenticationError("Password too long")
        user = self.user_repo.create(
            User(
                username=username,
                hashed_password=bcrypt.hashpw(
                    password.encode(), bcrypt.gensalt()
                ).decode(),
            )
        )
        household = self.household_repo.create(
            Household(name=f"{username}'s household")
        )
        self.user_household_repo.create(user.id, household.id)
        if invite_token:
            invited = self.household_repo.get_by_invite_token(invite_token)
            if invited and not self.user_household_repo.exists(user.id, invited.id):
                self.user_household_repo.create(user.id, invited.id)
        return user

    def login(self, username: str, password: str) -> dict[str, str]:
        if len(password) > 128:
            raise AuthenticationError("Password too long")
        user = self.user_repo.get_by_username(username)
        if not user or not bcrypt.checkpw(
            password.encode(), user.hashed_password.encode()
        ):
            raise AuthenticationError("Invalid username or password")
        access_token = self._create_access_token({"sub": str(user.id)})
        refresh_token = self._create_refresh_token(user.id)
        return {"access_token": access_token, "refresh_token": refresh_token}

    def refresh(self, refresh_token_raw: str) -> dict[str, str]:
        """Validate a refresh token, rotate it, and return new token pair."""
        if not self.refresh_token_repo:
            raise AuthenticationError("Refresh tokens are not configured")
        token_hash = hashlib.sha256(refresh_token_raw.encode()).hexdigest()
        stored = self.refresh_token_repo.get_by_hash(token_hash)
        if not stored:
            raise AuthenticationError("Invalid or expired refresh token")
        # Revoke the old token (rotation)
        self.refresh_token_repo.revoke(stored)
        # Issue new pair
        access_token = self._create_access_token({"sub": str(stored.user_id)})
        new_refresh_token = self._create_refresh_token(stored.user_id)
        return {"access_token": access_token, "refresh_token": new_refresh_token}

    def logout(self, user_id: int) -> None:
        """Revoke all refresh tokens for the user."""
        if self.refresh_token_repo:
            self.refresh_token_repo.revoke_all_for_user(user_id)

    def get_user_from_token(self, token: str) -> User:
        try:
            payload = jwt.decode(
                token, settings.secret_key, algorithms=[settings.algorithm]
            )
            user_id = int(payload.get("sub"))
        except (JWTError, TypeError, ValueError):
            raise AuthenticationError("Invalid token")
        user = self.user_repo.get(user_id)
        if not user:
            raise AuthenticationError("User not found")
        return user

    def _create_access_token(self, data: dict) -> str:
        payload = data.copy()
        payload["exp"] = datetime.now(timezone.utc) + timedelta(
            minutes=settings.access_token_expire_minutes
        )
        payload["type"] = "access"
        return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)

    def _create_refresh_token(self, user_id: int) -> str:
        """Generate a random refresh token, store its hash in DB, return raw token."""
        if not self.refresh_token_repo:
            raise AuthenticationError("Refresh tokens are not configured")
        raw_token = secrets.token_urlsafe(48)
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        self.refresh_token_repo.create(
            RefreshToken(
                user_id=user_id,
                token_hash=token_hash,
                expires_at=datetime.now(timezone.utc)
                + timedelta(days=settings.refresh_token_expire_days),
            )
        )
        return raw_token
