import pytest
from fastapi.testclient import TestClient

from kevin.api.v1.dependencies import get_household
from kevin.database import get_session
from kevin.main import app
from tests.helpers import create_household


@pytest.fixture
def client(session):
    def override_get_session():
        yield session

    def override_household(household_id: int) -> int:
        return household_id

    app.dependency_overrides[get_session] = override_get_session
    app.dependency_overrides[get_household] = override_household
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()


def _asset_url(household_id: int) -> str:
    return f"/api/v1/households/{household_id}/year/2026/month/2/asset"


def test_create_asset_returns_carry_forward_fields(client, session):
    household = create_household(session)

    response = client.post(
        _asset_url(household.id) + "/",
        json={
            "title": "Brokerage",
            "price": "110.00",
            "amount": "10.5",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["id"] > 0
    assert body["carried_forward"] is False
    assert body["previous_asset_id"] is None
    assert body["amount"] == 10.5
    assert body["price"] == 110.0


def test_create_asset_accepts_explicit_carried_forward(client, session):
    household = create_household(session)

    response = client.post(
        _asset_url(household.id) + "/",
        json={"title": "Brokerage", "carried_forward": True},
    )

    assert response.status_code == 201
    assert response.json()["carried_forward"] is True


def test_update_without_carried_forward_keeps_existing_value(client, session):
    household = create_household(session)
    created = client.post(
        _asset_url(household.id) + "/",
        json={"title": "Brokerage", "carried_forward": True},
    ).json()

    response = client.put(
        f"{_asset_url(household.id)}/{created['id']}",
        json={"title": "Updated brokerage", "price": "250.00"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "Updated brokerage"
    assert body["price"] == 250.0
    assert body["carried_forward"] is True


def test_update_can_explicitly_clear_carried_forward(client, session):
    household = create_household(session)
    created = client.post(
        _asset_url(household.id) + "/",
        json={"title": "Brokerage", "carried_forward": True},
    ).json()

    response = client.put(
        f"{_asset_url(household.id)}/{created['id']}",
        json={"title": "Brokerage", "carried_forward": False},
    )

    assert response.status_code == 200
    assert response.json()["carried_forward"] is False


def test_list_and_get_asset_include_carry_forward_fields(client, session):
    household = create_household(session)
    created = client.post(
        _asset_url(household.id) + "/",
        json={"title": "Brokerage"},
    ).json()

    listed = client.get(_asset_url(household.id) + "/")
    fetched = client.get(f"{_asset_url(household.id)}/{created['id']}")

    assert listed.status_code == 200
    assert len(listed.json()) == 1
    assert listed.json()[0]["carried_forward"] is False
    assert fetched.status_code == 200
    assert fetched.json()["previous_asset_id"] is None
