from datetime import datetime, timezone
from decimal import Decimal

import bcrypt

from kevin.models.household import Household
from kevin.models.user import User
from kevin.repositories.asset import AssetRepository
from kevin.repositories.household import HouseholdRepository
from kevin.repositories.refresh_token import RefreshTokenRepository
from kevin.repositories.user import UserRepository
from kevin.repositories.user_household import UserHouseholdRepository
from kevin.services.auth import AuthService
from tests.helpers import create_asset


class FixedDateTime(datetime):
    @classmethod
    def now(cls, tz=None):
        fixed = datetime(2026, 3, 15, 12, 0, tzinfo=timezone.utc)
        return fixed if tz else fixed.replace(tzinfo=None)


def _auth_service(session) -> AuthService:
    return AuthService(
        UserRepository(session),
        HouseholdRepository(session),
        UserHouseholdRepository(session),
        RefreshTokenRepository(session),
        AssetRepository(session),
    )


def test_login_carries_forward_assets_for_all_households(session, monkeypatch):
    monkeypatch.setattr("kevin.services.auth.datetime", FixedDateTime)

    user = User(
        username="alice",
        hashed_password=bcrypt.hashpw(b"password123", bcrypt.gensalt()).decode(),
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    household_repo = HouseholdRepository(session)
    membership_repo = UserHouseholdRepository(session)
    households = [
        household_repo.create(Household(name="Home")),
        household_repo.create(Household(name="Cabin")),
    ]
    for household in households:
        membership_repo.create(user.id, household.id)
        create_asset(session, household.id, 2026, 2)

    tokens = _auth_service(session).login("alice", "password123")

    assert tokens["access_token"]
    assert tokens["refresh_token"]
    for household in households:
        carried = AssetRepository(session).list(household.id, 2026, 3)
        assert len(carried) == 1
        assert carried[0].previous_asset_id is not None
        assert carried[0].price == Decimal("100.00")


def test_login_does_not_fail_when_a_household_has_no_previous_assets(
    session, monkeypatch
):
    monkeypatch.setattr("kevin.services.auth.datetime", FixedDateTime)

    user = User(
        username="bob",
        hashed_password=bcrypt.hashpw(b"password123", bcrypt.gensalt()).decode(),
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    household = HouseholdRepository(session).create(Household(name="Empty"))
    UserHouseholdRepository(session).create(user.id, household.id)

    tokens = _auth_service(session).login("bob", "password123")

    assert tokens["access_token"]
    assert AssetRepository(session).list(household.id, 2026, 3) == []
