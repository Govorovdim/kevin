from sqlmodel import Session

from kevin.repositories.asset import AssetRepository
from kevin.repositories.expense import ExpenseRepository
from kevin.repositories.household import HouseholdRepository
from kevin.repositories.income import IncomeRepository
from kevin.repositories.liability import LiabilityRepository
from kevin.repositories.user_household import UserHouseholdRepository
from kevin.services.asset import AssetService
from kevin.services.currency import CurrencyService
from kevin.services.expense import ExpenseService
from kevin.services.gemini.handlers import ToolHandlers
from kevin.services.household import HouseholdService
from kevin.services.income import IncomeService
from kevin.services.liability import LiabilityService
from kevin.services.overview import OverviewService


def _make_handlers(
    session: Session, *, household_id: int | None = None, user_id: int = 1
) -> ToolHandlers:
    household_repo = HouseholdRepository(session)
    user_household_repo = UserHouseholdRepository(session)
    expense_repo = ExpenseRepository(session)
    income_repo = IncomeRepository(session)
    asset_repo = AssetRepository(session)
    liability_repo = LiabilityRepository(session)

    return ToolHandlers(
        session=session,
        user_id=user_id,
        household_id=household_id,
        expense_service=ExpenseService(expense_repo),
        income_service=IncomeService(income_repo),
        asset_service=AssetService(asset_repo),
        liability_service=LiabilityService(liability_repo),
        overview_service=OverviewService(
            expense_repo, income_repo, asset_repo, liability_repo
        ),
        currency_service=CurrencyService(),
        user_household_repo=user_household_repo,
        household_service=HouseholdService(household_repo, user_household_repo),
    )


def test_create_household_adds_membership_and_normalizes_currency(session):
    handlers = _make_handlers(session)

    result = handlers.execute(
        "create_household", {"name": "  Vacation Home  ", "currency": "eur"}
    )

    assert result["success"] is True
    households = HouseholdRepository(session).list_by_user(1)
    assert [h.name for h in households] == ["Vacation Home"]
    assert households[0].currency == "EUR"


def test_create_household_allowed_when_scoped_to_active_household(session):
    handlers = _make_handlers(session, household_id=999)

    result = handlers.execute("create_household", {"name": "Second Home"})

    assert result["success"] is True
    households = HouseholdRepository(session).list_by_user(1)
    assert [h.name for h in households] == ["Second Home"]
    assert households[0].currency == "USD"


def test_create_household_rejects_invalid_input(session):
    handlers = _make_handlers(session)

    missing_name = handlers.execute("create_household", {"name": "   "})
    bad_currency = handlers.execute(
        "create_household", {"name": "Home", "currency": "US"}
    )

    assert missing_name["success"] is False
    assert bad_currency["success"] is False
    assert HouseholdRepository(session).list_by_user(1) == []


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _create_household(session, handlers, name: str = "Test home", user_id: int = 1):
    result = handlers.execute("create_household", {"name": name})
    assert result["success"] is True
    return next(
        h for h in HouseholdRepository(session).list_by_user(user_id) if h.name == name
    )


def _add_expense(
    handlers, household_id: int, title: str, amount: float, month: int = 1
):
    result = handlers.execute(
        "add_expense",
        {
            "household_id": household_id,
            "year": 2026,
            "month": month,
            "title": title,
            "amount": amount,
        },
    )
    assert result["success"] is True
    return result


# ---------------------------------------------------------------------------
# Move / copy / bulk
# ---------------------------------------------------------------------------


def test_move_record_changes_month(session):
    handlers = _make_handlers(session)
    household = _create_household(session, handlers)
    _add_expense(handlers, household.id, "Rent", 1000)
    expense = ExpenseRepository(session).list(household.id, 2026, 1)[0]

    result = handlers.execute(
        "move_record",
        {
            "household_id": household.id,
            "record_type": "expense",
            "record_id": expense.id,
            "to_year": 2026,
            "to_month": 2,
        },
    )

    assert result["success"] is True
    assert ExpenseRepository(session).list(household.id, 2026, 1) == []
    assert [
        e.title for e in ExpenseRepository(session).list(household.id, 2026, 2)
    ] == ["Rent"]


def test_move_record_rejects_assets(session):
    handlers = _make_handlers(session)
    household = _create_household(session, handlers)
    handlers.execute(
        "add_asset",
        {
            "household_id": household.id,
            "year": 2026,
            "month": 1,
            "title": "Brokerage",
            "price": 100,
        },
    )
    asset = AssetRepository(session).list(household.id, 2026, 1)[0]

    result = handlers.execute(
        "move_record",
        {
            "household_id": household.id,
            "record_type": "asset",
            "record_id": asset.id,
            "to_year": 2026,
            "to_month": 2,
        },
    )

    assert result["success"] is False
    assert "carried forward" in result["detail"]


def test_copy_month_copies_and_skips_existing(session):
    handlers = _make_handlers(session)
    household = _create_household(session, handlers)
    _add_expense(handlers, household.id, "Rent", 1000)
    handlers.execute(
        "add_income",
        {
            "household_id": household.id,
            "year": 2026,
            "month": 1,
            "title": "Salary",
            "amount": 5000,
        },
    )
    handlers.execute(
        "add_asset",
        {
            "household_id": household.id,
            "year": 2026,
            "month": 1,
            "title": "Brokerage",
            "price": 100,
        },
    )

    first = handlers.execute(
        "copy_month",
        {
            "household_id": household.id,
            "from_year": 2026,
            "from_month": 1,
            "to_year": 2026,
            "to_month": 2,
        },
    )
    second = handlers.execute(
        "copy_month",
        {
            "household_id": household.id,
            "from_year": 2026,
            "from_month": 1,
            "to_year": 2026,
            "to_month": 2,
        },
    )

    assert first["success"] is True
    assert "Copied 2 record(s)" in first["detail"]
    assert "skipped 2 already present" in second["detail"]
    assert len(ExpenseRepository(session).list(household.id, 2026, 2)) == 1
    assert len(IncomeRepository(session).list(household.id, 2026, 2)) == 1
    assert AssetRepository(session).list(household.id, 2026, 2) == []


def test_add_records_bulk_reports_partial_failures(session):
    handlers = _make_handlers(session)
    household = _create_household(session, handlers)

    result = handlers.execute(
        "add_records_bulk",
        {
            "household_id": household.id,
            "year": 2026,
            "month": 3,
            "records": [
                {"record_type": "expense", "title": "Groceries", "amount": 120.5},
                {"record_type": "income", "title": "Bonus", "amount": 300},
                {
                    "record_type": "asset",
                    "title": "Brokerage",
                    "price": 100,
                    "quantity": 2,
                },
                {"record_type": "expense", "title": "  ", "amount": 10},
            ],
        },
    )

    assert result["success"] is True
    assert "Added 3 record(s)" in result["detail"]
    assert "1 failed" in result["detail"]
    assert len(ExpenseRepository(session).list(household.id, 2026, 3)) == 1
    assert len(IncomeRepository(session).list(household.id, 2026, 3)) == 1
    assert len(AssetRepository(session).list(household.id, 2026, 3)) == 1


# ---------------------------------------------------------------------------
# Duplicate detection
# ---------------------------------------------------------------------------


def test_find_duplicates_groups_matching_records(session):
    handlers = _make_handlers(session)
    household = _create_household(session, handlers)
    _add_expense(handlers, household.id, "Coffee", 5)
    _add_expense(handlers, household.id, " coffee ", 5)
    _add_expense(handlers, household.id, "Coffee", 6)
    _add_expense(handlers, household.id, "Coffee", 5, month=2)

    result = handlers.execute(
        "find_duplicates",
        {"household_id": household.id, "record_type": "expense"},
    )

    assert result["success"] is True
    assert "Found 2 records in 1 duplicate group(s)" in result["detail"]
    assert "in 1/2026" in result["detail"]


# ---------------------------------------------------------------------------
# Household lifecycle
# ---------------------------------------------------------------------------


def test_rename_household(session):
    handlers = _make_handlers(session)
    household = _create_household(session, handlers)

    result = handlers.execute(
        "rename_household", {"household_id": household.id, "name": "New name"}
    )

    assert result["success"] is True
    assert HouseholdRepository(session).get(household.id).name == "New name"


def test_generate_invite_and_join_household(session):
    owner_handlers = _make_handlers(session)
    household = _create_household(session, owner_handlers)

    invite = owner_handlers.execute(
        "generate_household_invite", {"household_id": household.id}
    )
    assert invite["success"] is True
    token = invite["detail"].rsplit(": ", 1)[1]

    joiner_handlers = _make_handlers(session, user_id=2)
    joined = joiner_handlers.execute("join_household", {"token": token})

    assert joined["success"] is True
    assert HouseholdRepository(session).list_by_user(2)[0].id == household.id


def test_leave_household_requires_confirmation_and_another_household(session):
    handlers = _make_handlers(session)
    household = _create_household(session, handlers)

    no_confirm = handlers.execute(
        "leave_household", {"household_id": household.id, "confirm": False}
    )
    only_household = handlers.execute(
        "leave_household", {"household_id": household.id, "confirm": True}
    )

    assert no_confirm["success"] is False
    assert "confirmation" in no_confirm["detail"]
    assert only_household["success"] is False
    assert "only household" in only_household["detail"]


def test_leave_household_removes_membership(session):
    handlers = _make_handlers(session)
    household = _create_household(session, handlers, name="First")
    _create_household(session, handlers, name="Second")

    result = handlers.execute(
        "leave_household", {"household_id": household.id, "confirm": True}
    )

    assert result["success"] is True
    names = [h.name for h in HouseholdRepository(session).list_by_user(1)]
    assert names == ["Second"]


def test_delete_household_requires_confirmation(session):
    handlers = _make_handlers(session)
    household = _create_household(session, handlers, name="First")

    result = handlers.execute(
        "delete_household", {"household_id": household.id, "confirm": False}
    )

    assert result["success"] is False
    assert "confirmation" in result["detail"]


def test_delete_household_rejects_only_household(session):
    handlers = _make_handlers(session)
    household = _create_household(session, handlers)

    result = handlers.execute(
        "delete_household", {"household_id": household.id, "confirm": True}
    )

    assert result["success"] is False
    assert "only household" in result["detail"]


def test_delete_household_rejects_household_with_other_members(session):
    owner_handlers = _make_handlers(session)
    household = _create_household(session, owner_handlers)
    invite = owner_handlers.execute(
        "generate_household_invite", {"household_id": household.id}
    )
    token = invite["detail"].rsplit(": ", 1)[1]
    _make_handlers(session, user_id=2).execute("join_household", {"token": token})
    _create_household(session, owner_handlers, name="Second")

    result = owner_handlers.execute(
        "delete_household", {"household_id": household.id, "confirm": True}
    )

    assert result["success"] is False
    assert "other members" in result["detail"]


def test_delete_household_deletes_records(session):
    handlers = _make_handlers(session)
    household = _create_household(session, handlers, name="First")
    _create_household(session, handlers, name="Second")
    _add_expense(handlers, household.id, "Rent", 1000)

    result = handlers.execute(
        "delete_household", {"household_id": household.id, "confirm": True}
    )

    assert result["success"] is True
    assert [h.name for h in HouseholdRepository(session).list_by_user(1)] == ["Second"]
    assert UserHouseholdRepository(session).exists(1, household.id) is False
