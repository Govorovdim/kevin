from decimal import Decimal

import pytest

from kevin.models.asset import Asset
from kevin.repositories.asset import AssetRepository
from kevin.services.asset import AssetService
from tests.helpers import create_asset, create_household


def _service(session) -> AssetService:
    return AssetService(AssetRepository(session))


def test_carries_assets_into_current_month(session):
    household = create_household(session)
    january = create_asset(session, household.id, 2026, 1)

    _service(session).carry_forward_previous_month(household.id, 2026, 2)

    session.refresh(january)
    assert january.carried_forward is True

    february = AssetRepository(session).list(household.id, 2026, 2)
    assert len(february) == 1
    carried = february[0]
    assert carried.previous_asset_id == january.id
    assert carried.carried_forward is False
    assert carried.title == january.title
    assert carried.price == january.price
    assert carried.amount == january.amount


def test_existing_successor_is_not_duplicated(session):
    household = create_household(session)
    january = create_asset(session, household.id, 2026, 1)
    create_asset(
        session,
        household.id,
        2026,
        2,
        previous_asset_id=january.id,
    )

    _service(session).carry_forward_previous_month(household.id, 2026, 2)

    session.refresh(january)
    assert january.carried_forward is True
    assert len(AssetRepository(session).list(household.id, 2026, 2)) == 1


def test_already_carried_asset_is_not_carried_again(session):
    household = create_household(session)
    create_asset(session, household.id, 2026, 1, carried_forward=True)

    _service(session).carry_forward_previous_month(household.id, 2026, 2)

    assert AssetRepository(session).list(household.id, 2026, 2) == []


def test_january_carries_from_previous_december(session):
    household = create_household(session)
    december = create_asset(session, household.id, 2025, 12)

    _service(session).carry_forward_previous_month(household.id, 2026, 1)

    january = AssetRepository(session).list(household.id, 2026, 1)
    assert len(january) == 1
    assert january[0].previous_asset_id == december.id


def test_deleting_a_carried_asset_keeps_its_source_flagged(session):
    household = create_household(session)
    january = create_asset(session, household.id, 2026, 1, carried_forward=True)
    february = create_asset(
        session,
        household.id,
        2026,
        2,
        previous_asset_id=january.id,
    )

    _service(session).delete(february.id, household.id, 2026, 2)

    session.refresh(january)
    assert january.carried_forward is True
    assert AssetRepository(session).list(household.id, 2026, 2) == []


def test_rolls_back_the_whole_carry_forward_on_failure(session, monkeypatch):
    household = create_household(session)
    january = create_asset(session, household.id, 2026, 1)
    service = _service(session)

    def fail_create(asset):
        raise RuntimeError("database write failed")

    monkeypatch.setattr(service.repository, "create_without_commit", fail_create)

    with pytest.raises(RuntimeError, match="database write failed"):
        service.carry_forward_previous_month(household.id, 2026, 2)

    session.expire_all()
    stored = session.get(Asset, january.id)
    assert stored is not None
    assert stored.carried_forward is False
    assert AssetRepository(session).list(household.id, 2026, 2) == []


def test_portfolio_value_treats_missing_and_zero_amount_as_one(session):
    household = create_household(session)
    create_asset(
        session,
        household.id,
        2026,
        1,
        title="Missing amount",
        price=Decimal("100.00"),
        amount=None,
    )
    create_asset(
        session,
        household.id,
        2026,
        1,
        title="Zero amount",
        price=Decimal("50.00"),
        amount=Decimal("0"),
    )
    create_asset(
        session,
        household.id,
        2026,
        1,
        title="Explicit amount",
        price=Decimal("10.00"),
        amount=Decimal("3"),
    )

    value = _service(session).portfolio_value(household.id, 2026, 1)

    assert value == Decimal("180.00")
