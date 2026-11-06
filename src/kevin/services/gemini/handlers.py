"""Gemini tool handler implementations."""

from collections import defaultdict
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
from kevin.services.household import HouseholdService
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


def _normalize_title(title: str) -> str:
    """Normalize a record title for duplicate comparison."""
    return " ".join(title.lower().split())


def _require_month(value: Any, field: str) -> int:
    """Parse and validate a 1-12 month value."""
    month = int(value)
    if not 1 <= month <= 12:
        raise ValueError(f"{field} must be between 1 and 12")
    return month


class ToolHandlers:
    """Dispatches and executes Gemini tool calls."""

    def __init__(
        self,
        *,
        session: Session,
        user_id: int,
        household_id: int | None = None,
        expense_service: ExpenseService,
        income_service: IncomeService,
        asset_service: AssetService,
        liability_service: LiabilityService,
        overview_service: OverviewService,
        currency_service: CurrencyService,
        user_household_repo: UserHouseholdRepository,
        household_service: HouseholdService,
    ) -> None:
        self._session = session
        self._user_id = user_id
        self._household_id = household_id
        self._expense_service = expense_service
        self._income_service = income_service
        self._asset_service = asset_service
        self._liability_service = liability_service
        self._overview_service = overview_service
        self._currency_service = currency_service
        self._user_household_repo = user_household_repo
        self._household_service = household_service

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

    def _handle_create_household(self, args: dict[str, Any]) -> str:
        name = str(args.get("name") or "").strip()
        if not name:
            raise ValueError("Household name is required")
        if len(name) > 255:
            raise ValueError("Household name must be 255 characters or fewer")

        currency = str(args.get("currency") or "USD").strip().upper()
        if len(currency) != 3 or not currency.isalpha():
            raise ValueError(
                f"Invalid currency '{currency}'. "
                "Use a 3-letter ISO 4217 code such as USD or EUR."
            )

        household = self._household_service.create(self._user_id, name, currency)
        return (
            f"Created household '{household.name}' "
            f"(id={household.id}, currency={household.currency})"
        )

    def _handle_rename_household(self, args: dict[str, Any]) -> str:
        household_id = self._require_household_access(args)
        name = str(args.get("name") or "").strip()
        if not name:
            raise ValueError("Household name is required")
        if len(name) > 255:
            raise ValueError("Household name must be 255 characters or fewer")

        household = self._household_service.update(household_id, name)
        return f"Renamed household #{household_id} to '{household.name}'"

    def _handle_generate_household_invite(self, args: dict[str, Any]) -> str:
        household_id = self._require_household_access(args)
        household = self._household_service.generate_invite(household_id)
        return (
            f"Invite token for household '{household.name}': {household.invite_token}"
        )

    def _handle_join_household(self, args: dict[str, Any]) -> str:
        token = str(args.get("token") or "").strip()
        if not token:
            raise ValueError("Invite token is required")

        household = self._household_service.join_by_invite(self._user_id, token)
        return (
            f"Joined household '{household.name}' "
            f"(id={household.id}, currency={household.currency})"
        )

    def _handle_leave_household(self, args: dict[str, Any]) -> str:
        if not args.get("confirm"):
            raise ValueError("Leaving a household requires explicit user confirmation")
        household_id = self._require_household_access(args)
        household = self._household_service.get(household_id)

        if len(self._user_household_repo.list_household_ids(self._user_id)) <= 1:
            raise ValueError(
                "You can't leave your only household. "
                "Create or join another household first."
            )

        self._household_service.leave(self._user_id, household_id)
        return f"You left household '{household.name}'"

    def _handle_delete_household(self, args: dict[str, Any]) -> str:
        if not args.get("confirm"):
            raise ValueError("Deleting a household requires explicit user confirmation")
        household_id = self._require_household_access(args)
        household = self._household_service.get(household_id)

        if self._user_household_repo.count_by_household(household_id) > 1:
            raise ValueError(
                "Cannot delete a household with other members. "
                "Ask them to leave first, or leave it yourself."
            )
        if len(self._user_household_repo.list_household_ids(self._user_id)) <= 1:
            raise ValueError(
                "You can't delete your only household. Create another household first."
            )

        self._household_service.delete(household_id)
        return f"Deleted household '{household.name}' and all of its records"

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
            Decimal(str(args["price"])),
            Decimal(str(args["amount"])) if args.get("amount") is not None else None,
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
        existing = self._asset_service.get(
            int(args["asset_id"]),
            household_id,
            int(args["year"]),
            int(args["month"]),
        )
        price = args.get("price")
        amount = args.get("amount")
        asset = self._asset_service.update(
            int(args["asset_id"]),
            household_id,
            int(args["year"]),
            int(args["month"]),
            args["title"],
            Decimal(str(price)) if price is not None else existing.price,
            Decimal(str(amount)) if amount is not None else existing.amount,
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
    # Bulk / month tools
    # ------------------------------------------------------------------

    def _handle_move_record(self, args: dict[str, Any]) -> str:
        household_id = self._require_household_access(args)
        record_type = str(args.get("record_type") or "").lower().strip()
        record_id = int(args["record_id"])
        to_year = int(args["to_year"])
        to_month = _require_month(args["to_month"], "to_month")

        if record_type == "asset":
            raise ValueError(
                "Assets can't be moved between months because they are carried "
                "forward automatically."
            )

        services = {
            "expense": self._expense_service,
            "income": self._income_service,
            "liability": self._liability_service,
        }
        service = services.get(record_type)
        if service is None:
            raise ValueError("record_type must be 'expense', 'income', or 'liability'")

        record = service.move(record_id, household_id, to_year, to_month)
        return f"Moved {record_type} '{record.title}' to {to_month}/{to_year}"

    def _handle_copy_month(self, args: dict[str, Any]) -> str:
        household_id = self._require_household_access(args)
        from_year = int(args["from_year"])
        from_month = _require_month(args["from_month"], "from_month")
        to_year = int(args["to_year"])
        to_month = _require_month(args["to_month"], "to_month")

        if (from_year, from_month) == (to_year, to_month):
            raise ValueError("Source and destination months are the same")

        record_types = self._parse_copy_record_types(args.get("record_types"))
        services = {
            "expense": self._expense_service,
            "income": self._income_service,
            "liability": self._liability_service,
        }

        copied = 0
        skipped = 0
        for record_type in record_types:
            service = services[record_type]
            source = service.list(household_id, from_year, from_month)
            target = service.list(household_id, to_year, to_month)
            existing_titles = {_normalize_title(r.title) for r in target}

            for record in source:
                title_key = _normalize_title(record.title)
                if title_key in existing_titles:
                    skipped += 1
                    continue

                service.create(
                    household_id,
                    to_year,
                    to_month,
                    record.title,
                    record.amount,
                )
                existing_titles.add(title_key)
                copied += 1

        if copied == 0 and skipped == 0:
            return (
                f"No expense, income, or liability records found in "
                f"{from_month}/{from_year}."
            )

        detail = (
            f"Copied {copied} record(s) from {from_month}/{from_year} to "
            f"{to_month}/{to_year}"
        )
        if skipped:
            detail += f"; skipped {skipped} already present"
        return detail

    def _handle_add_records_bulk(self, args: dict[str, Any]) -> str:
        household_id = self._require_household_access(args)
        year = int(args["year"])
        month = _require_month(args["month"], "month")
        records = args.get("records")

        if not isinstance(records, list) or not records:
            raise ValueError("No records provided")

        created: list[str] = []
        errors: list[str] = []

        for index, item in enumerate(records, start=1):
            try:
                record_type = str(item.get("record_type") or "").lower().strip()
                title = str(item.get("title") or "").strip()
                if not title:
                    raise ValueError("title is required")

                if record_type == "expense":
                    record = self._expense_service.create(
                        household_id,
                        year,
                        month,
                        title,
                        Decimal(str(item.get("amount"))),
                    )
                elif record_type == "income":
                    record = self._income_service.create(
                        household_id,
                        year,
                        month,
                        title,
                        Decimal(str(item.get("amount"))),
                    )
                elif record_type == "liability":
                    record = self._liability_service.create(
                        household_id,
                        year,
                        month,
                        title,
                        Decimal(str(item.get("amount"))),
                    )
                elif record_type == "asset":
                    quantity = item.get("quantity")
                    record = self._asset_service.create(
                        household_id,
                        year,
                        month,
                        title,
                        Decimal(str(item.get("price"))),
                        Decimal(str(quantity)) if quantity is not None else None,
                    )
                else:
                    raise ValueError(
                        "record_type must be 'expense', 'income', 'asset', "
                        "or 'liability'"
                    )

                created.append(f"{record_type} '{record.title}'")
            except Exception as e:
                errors.append(f"row {index}: {e}")

        if not created:
            raise ValueError("No records were added. " + "; ".join(errors))

        detail = f"Added {len(created)} record(s) to {month}/{year}"
        if errors:
            detail += f"; {len(errors)} failed: " + "; ".join(errors)
        return detail

    @staticmethod
    def _parse_copy_record_types(value: Any) -> list[str]:
        raw = str(value or "all").lower().strip()
        if not raw or raw == "all":
            return ["expense", "income", "liability"]

        aliases = {
            "expenses": "expense",
            "incomes": "income",
            "liabilities": "liability",
        }
        record_types: list[str] = []
        for token in raw.split(","):
            token = aliases.get(token.strip(), token.strip())
            if token == "asset":
                raise ValueError(
                    "Assets can't be copied between months because they carry "
                    "forward automatically"
                )
            if token not in ("expense", "income", "liability"):
                raise ValueError(
                    "record_types must contain only 'expense', 'income', "
                    "'liability', or 'all'"
                )
            if token not in record_types:
                record_types.append(token)

        return record_types

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

    def _handle_find_duplicates(self, args: dict[str, Any]) -> str:
        record_type = str(args.get("record_type") or "all").lower().strip()
        household_ids = self._resolve_household_ids(args.get("household_id"))
        year = args.get("year")
        month = args.get("month")

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

        groups: dict[tuple[Any, ...], list[Any]] = defaultdict(list)
        for model in models_to_search:
            stmt = select(model).where(model.household_id.in_(household_ids))
            if year:
                stmt = stmt.where(model.year == int(year))
            if month:
                stmt = stmt.where(model.month == int(month))

            for record in self._session.exec(stmt).all():
                key = (
                    record.household_id,
                    record.year,
                    record.month,
                    model.__name__.lower(),
                    _normalize_title(record.title),
                    getattr(record, "amount", None),
                    getattr(record, "price", None),
                )
                groups[key].append(record)

        duplicates = {key: items for key, items in groups.items() if len(items) > 1}
        if not duplicates:
            return "No duplicate records found."

        lines: list[str] = []
        total = 0
        for key in sorted(duplicates, key=lambda k: (k[0], k[1], k[2], k[3], k[4])):
            household_id, rec_year, rec_month, type_name, _, _, _ = key
            records = duplicates[key]
            total += len(records)
            first = records[0]

            description = f"[{type_name}] '{first.title}'"
            if type_name == "asset":
                description += f" price={first.price}"
                if first.amount is not None:
                    description += f" quantity={first.amount}"
            else:
                description += f" amount={first.amount}"

            ids = ", ".join(str(r.id) for r in records)
            lines.append(
                f"{description} in {rec_month}/{rec_year} "
                f"(household_id={household_id}): ids {ids}"
            )

        return (
            f"Found {total} records in {len(duplicates)} duplicate group(s):\n"
            + "\n".join(lines)
        )

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
        "create_household": "_handle_create_household",
        "rename_household": "_handle_rename_household",
        "generate_household_invite": "_handle_generate_household_invite",
        "join_household": "_handle_join_household",
        "leave_household": "_handle_leave_household",
        "delete_household": "_handle_delete_household",
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
        "move_record": "_handle_move_record",
        "copy_month": "_handle_copy_month",
        "add_records_bulk": "_handle_add_records_bulk",
        "get_overview": "_handle_get_overview",
        "search_records": "_handle_search_records",
        "find_duplicates": "_handle_find_duplicates",
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

        When the service is scoped to a specific household (self._household_id),
        only that household is allowed regardless of what the AI requests.

        Returns:
            The validated household_id.

        Raises:
            PermissionError: If the user doesn't have access or the requested
                household doesn't match the scoped household.
        """
        household_id = int(args["household_id"])

        if self._household_id is not None and household_id != self._household_id:
            raise PermissionError(
                f"Operations are scoped to household {self._household_id}. "
                f"Cannot operate on household {household_id}."
            )

        if not self._user_household_repo.exists(self._user_id, household_id):
            raise PermissionError(f"You don't have access to household {household_id}")
        return household_id

    def _resolve_household_ids(self, household_id: Any) -> list[int]:
        """Resolve which household IDs to query.

        When the service is scoped to a specific household (self._household_id),
        always returns only that household regardless of args.
        If a specific household_id is given, verify access and return it.
        Otherwise, return all household IDs the user belongs to.
        """
        if self._household_id is not None:
            if household_id and int(household_id) != self._household_id:
                raise PermissionError(
                    f"Operations are scoped to household {self._household_id}. "
                    f"Cannot query household {household_id}."
                )
            return [self._household_id]

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
