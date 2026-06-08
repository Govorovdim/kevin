"""Gemini tool handler implementations."""

from decimal import Decimal
from typing import Any

from sqlmodel import Session, select

from kevin.models.asset import Asset
from kevin.models.expense import Expense
from kevin.models.income import Income
from kevin.models.liability import Liability
from kevin.models.user_household import UserHousehold
from kevin.repositories.household import HouseholdRepository
from kevin.repositories.user_household import UserHouseholdRepository
from kevin.services.asset import AssetService
from kevin.services.currency import CurrencyError, CurrencyService
from kevin.services.expense import ExpenseService
from kevin.services.income import IncomeService
from kevin.services.liability import LiabilityService
from kevin.services.overview import OverviewService


def _serialize_decimals(obj: Any) -> Any:
    """Recursively convert Decimal values to float for JSON compatibility."""
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, dict):
        return {k: _serialize_decimals(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_serialize_decimals(item) for item in obj]
    return obj


class ToolHandlers:
    """Dispatches and executes Gemini tool calls."""

    def __init__(
        self,
        *,
        session: Session,
        user_id: int,
        expense_service: ExpenseService,
        income_service: IncomeService,
        asset_service: AssetService,
        liability_service: LiabilityService,
        overview_service: OverviewService,
        currency_service: CurrencyService,
        user_household_repo: UserHouseholdRepository,
    ) -> None:
        self._session = session
        self._user_id = user_id
        self._expense_service = expense_service
        self._income_service = income_service
        self._asset_service = asset_service
        self._liability_service = liability_service
        self._overview_service = overview_service
        self._currency_service = currency_service
        self._user_household_repo = user_household_repo

    def execute(self, tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
        """Dispatch a tool call and return a standardized action result.

        Returns:
            Dict with keys: action (str), success (bool), detail (str).
        """
        handler = self._get_handler(tool_name)
        if handler is None:
            return {
                "action": tool_name,
                "success": False,
                "detail": f"Unknown tool: {tool_name}",
            }

        try:
            detail = handler(args)
            return {"action": tool_name, "success": True, "detail": detail}
        except PermissionError as e:
            return {"action": tool_name, "success": False, "detail": str(e)}
        except Exception as e:
            return {"action": tool_name, "success": False, "detail": str(e)}

    # ------------------------------------------------------------------
    # Household tools
    # ------------------------------------------------------------------

    def _handle_list_households(self, args: dict[str, Any]) -> str:
        repo = HouseholdRepository(self._session)
        households = repo.list_by_user(self._user_id)
        if not households:
            return "You don't belong to any households yet."
        items = [f"- {h.name} (id={h.id}, currency={h.currency})" for h in households]
        return "Your households:\n" + "\n".join(items)

    # ------------------------------------------------------------------
    # Expense tools
    # ------------------------------------------------------------------

    def _handle_add_expense(self, args: dict[str, Any]) -> str:
        household_id = self._require_household_access(args)
        expense = self._expense_service.create(
            household_id,
            int(args["year"]),
            int(args["month"]),
            args["title"],
            Decimal(str(args["amount"])),
        )
        return f"Added expense '{expense.title}' for {expense.amount}"

    def _handle_remove_expense(self, args: dict[str, Any]) -> str:
        household_id = self._require_household_access(args)
        self._expense_service.delete(
            int(args["expense_id"]),
            household_id,
            int(args["year"]),
            int(args["month"]),
        )
        return f"Removed expense #{args['expense_id']}"

    def _handle_update_expense(self, args: dict[str, Any]) -> str:
        household_id = self._require_household_access(args)
        expense = self._expense_service.update(
            int(args["expense_id"]),
            household_id,
            int(args["year"]),
            int(args["month"]),
            args["title"],
            Decimal(str(args["amount"])),
        )
        return (
            f"Updated expense #{args['expense_id']} "
            f"to '{expense.title}' for {expense.amount}"
        )

    # ------------------------------------------------------------------
    # Income tools
    # ------------------------------------------------------------------

    def _handle_add_income(self, args: dict[str, Any]) -> str:
        household_id = self._require_household_access(args)
        income = self._income_service.create(
            household_id,
            int(args["year"]),
            int(args["month"]),
            args["title"],
            Decimal(str(args["amount"])),
        )
        return f"Added income '{income.title}' for {income.amount}"

    def _handle_remove_income(self, args: dict[str, Any]) -> str:
        household_id = self._require_household_access(args)
        self._income_service.delete(
            int(args["income_id"]),
            household_id,
            int(args["year"]),
            int(args["month"]),
        )
        return f"Removed income #{args['income_id']}"

    def _handle_update_income(self, args: dict[str, Any]) -> str:
        household_id = self._require_household_access(args)
        income = self._income_service.update(
            int(args["income_id"]),
            household_id,
            int(args["year"]),
            int(args["month"]),
            args["title"],
            Decimal(str(args["amount"])),
        )
        return (
            f"Updated income #{args['income_id']} "
            f"to '{income.title}' for {income.amount}"
        )

    # ------------------------------------------------------------------
    # Asset tools
    # ------------------------------------------------------------------

    def _handle_add_asset(self, args: dict[str, Any]) -> str:
        household_id = self._require_household_access(args)
        asset = self._asset_service.create(
            household_id,
            int(args["year"]),
            int(args["month"]),
            args["title"],
            args.get("ticker"),
            Decimal(str(args["amount"])) if args.get("amount") else None,
            Decimal(str(args["bought_price"])) if args.get("bought_price") else None,
            Decimal(str(args["current_price"])) if args.get("current_price") else None,
        )
        return f"Added asset '{asset.title}'"

    def _handle_remove_asset(self, args: dict[str, Any]) -> str:
        household_id = self._require_household_access(args)
        self._asset_service.delete(
            int(args["asset_id"]),
            household_id,
            int(args["year"]),
            int(args["month"]),
        )
        return f"Removed asset #{args['asset_id']}"

    def _handle_update_asset(self, args: dict[str, Any]) -> str:
        household_id = self._require_household_access(args)
        asset = self._asset_service.update(
            int(args["asset_id"]),
            household_id,
            int(args["year"]),
            int(args["month"]),
            args["title"],
            args.get("ticker"),
            Decimal(str(args["amount"])) if args.get("amount") else None,
            Decimal(str(args["bought_price"])) if args.get("bought_price") else None,
            Decimal(str(args["current_price"])) if args.get("current_price") else None,
        )
        return f"Updated asset #{args['asset_id']} to '{asset.title}'"

    # ------------------------------------------------------------------
    # Liability tools
    # ------------------------------------------------------------------

    def _handle_add_liability(self, args: dict[str, Any]) -> str:
        household_id = self._require_household_access(args)
        liability = self._liability_service.create(
            household_id,
            int(args["year"]),
            int(args["month"]),
            args["title"],
            Decimal(str(args["amount"])),
        )
        return f"Added liability '{liability.title}' for {liability.amount}"

    def _handle_remove_liability(self, args: dict[str, Any]) -> str:
        household_id = self._require_household_access(args)
        self._liability_service.delete(
            int(args["liability_id"]),
            household_id,
            int(args["year"]),
            int(args["month"]),
        )
        return f"Removed liability #{args['liability_id']}"

    def _handle_update_liability(self, args: dict[str, Any]) -> str:
        household_id = self._require_household_access(args)
        liability = self._liability_service.update(
            int(args["liability_id"]),
            household_id,
            int(args["year"]),
            int(args["month"]),
            args["title"],
            Decimal(str(args["amount"])),
        )
        return (
            f"Updated liability #{args['liability_id']} "
            f"to '{liability.title}' for {liability.amount}"
        )

    # ------------------------------------------------------------------
    # Query / analytics tools
    # ------------------------------------------------------------------

    def _handle_get_overview(self, args: dict[str, Any]) -> str:
        household_id = self._require_household_access(args)
        year = int(args["year"])
        month = args.get("month")

        if month:
            overview = self._overview_service.get_month(household_id, year, int(month))
        else:
            overview = self._overview_service.get_year(household_id, year)

        data = _serialize_decimals(overview.model_dump())
        return str(data)

    def _handle_search_records(self, args: dict[str, Any]) -> str:
        query = args.get("query", "").lower().strip()
        record_type = args.get("record_type", "all")
        household_id = args.get("household_id")
        year = args.get("year")
        month = args.get("month")
        amount_min = args.get("amount_min")
        amount_max = args.get("amount_max")

        household_ids = self._resolve_household_ids(household_id)
        results: list[str] = []

        type_model_map: dict[str, type] = {
            "expense": Expense,
            "income": Income,
            "asset": Asset,
            "liability": Liability,
        }

        models_to_search = (
            [type_model_map[record_type]]
            if record_type in type_model_map
            else list(type_model_map.values())
        )

        for model in models_to_search:
            stmt = select(model).where(model.household_id.in_(household_ids))

            if query:
                stmt = stmt.where(model.title.ilike(f"%{query}%"))
            if year:
                stmt = stmt.where(model.year == int(year))
            if month:
                stmt = stmt.where(model.month == int(month))
            if amount_min is not None and hasattr(model, "amount"):
                stmt = stmt.where(model.amount >= Decimal(str(amount_min)))
            if amount_max is not None and hasattr(model, "amount"):
                stmt = stmt.where(model.amount <= Decimal(str(amount_max)))

            records = self._session.exec(stmt).all()
            for r in records:
                type_name = model.__name__.lower()
                amount_str = ""
                if hasattr(r, "amount") and r.amount is not None:
                    amount_str = f", amount={r.amount}"
                results.append(
                    f"[{type_name}] id={r.id}, household_id={r.household_id}, "
                    f"title='{r.title}', year={r.year}, month={r.month}{amount_str}"
                )

        if not results:
            search_desc = []
            if query:
                search_desc.append(f"title='{args.get('query', '')}'")
            if amount_min is not None:
                search_desc.append(f"amount_min={amount_min}")
            if amount_max is not None:
                search_desc.append(f"amount_max={amount_max}")
            return f"No records found matching {', '.join(search_desc) or 'criteria'}"

        return f"Found {len(results)} record(s):\n" + "\n".join(results)

    # ------------------------------------------------------------------
    # Currency tools
    # ------------------------------------------------------------------

    def _handle_convert_currency(self, args: dict[str, Any]) -> str:
        amount = float(args["amount"])
        from_currency = str(args["from_currency"]).strip().upper()
        to_currency = str(args["to_currency"]).strip().upper()

        try:
            result = self._currency_service.convert(amount, from_currency, to_currency)
            return str(result)
        except CurrencyError as e:
            return f"Currency conversion failed: {e}"
        except ValueError as e:
            return f"Invalid conversion parameters: {e}"

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    _HANDLER_MAP: dict[str, str] = {
        "list_households": "_handle_list_households",
        "add_expense": "_handle_add_expense",
        "remove_expense": "_handle_remove_expense",
        "update_expense": "_handle_update_expense",
        "add_income": "_handle_add_income",
        "remove_income": "_handle_remove_income",
        "update_income": "_handle_update_income",
        "add_asset": "_handle_add_asset",
        "remove_asset": "_handle_remove_asset",
        "update_asset": "_handle_update_asset",
        "add_liability": "_handle_add_liability",
        "remove_liability": "_handle_remove_liability",
        "update_liability": "_handle_update_liability",
        "get_overview": "_handle_get_overview",
        "search_records": "_handle_search_records",
        "convert_currency": "_handle_convert_currency",
    }

    def _get_handler(self, tool_name: str):
        """Look up the handler method for a given tool name."""
        method_name = self._HANDLER_MAP.get(tool_name)
        if method_name is None:
            return None
        return getattr(self, method_name, None)

    def _require_household_access(self, args: dict[str, Any]) -> int:
        """Extract household_id from args and verify user access.

        Returns:
            The validated household_id.

        Raises:
            PermissionError: If the user doesn't have access.
        """
        household_id = int(args["household_id"])
        if not self._user_household_repo.exists(self._user_id, household_id):
            raise PermissionError(f"You don't have access to household {household_id}")
        return household_id

    def _resolve_household_ids(self, household_id: Any) -> list[int]:
        """Resolve which household IDs to query.

        If a specific household_id is given, verify access and return it.
        Otherwise, return all household IDs the user belongs to.
        """
        if household_id:
            hid = int(household_id)
            if not self._user_household_repo.exists(self._user_id, hid):
                raise PermissionError(f"You don't have access to household {hid}")
            return [hid]

        memberships = self._session.exec(
            select(UserHousehold.household_id).where(
                UserHousehold.user_id == self._user_id
            )
        ).all()
        return list(memberships)
