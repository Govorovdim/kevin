import logging
import time
from decimal import Decimal
from typing import Any

from google import genai
from google.genai import types
from sqlmodel import Session, select

from kevin.models.asset import Asset
from kevin.models.expense import Expense
from kevin.models.income import Income
from kevin.models.liability import Liability
from kevin.models.user_household import UserHousehold
from kevin.repositories.asset import AssetRepository
from kevin.repositories.expense import ExpenseRepository
from kevin.repositories.household import HouseholdRepository
from kevin.repositories.income import IncomeRepository
from kevin.repositories.liability import LiabilityRepository
from kevin.repositories.user_household import UserHouseholdRepository
from kevin.services.asset import AssetService
from kevin.services.expense import ExpenseService
from kevin.services.income import IncomeService
from kevin.services.liability import LiabilityService
from kevin.services.overview import OverviewService
from kevin.settings import settings

logger = logging.getLogger(__name__)

# Retry configuration
MAX_RETRIES = 3
RETRY_BASE_DELAY = 1.0  # seconds
RETRY_MAX_DELAY = 8.0  # seconds

# HTTP status codes / error substrings considered retryable
_RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
_RETRYABLE_ERROR_KEYWORDS = (
    "service unavailable",
    "resource exhausted",
    "deadline exceeded",
    "internal error",
    "temporarily unavailable",
    "overloaded",
    "rate limit",
    "quota",
    "connection",
    "timeout",
    "503",
    "429",
)


class GeminiError(Exception):
    """Base error for Gemini service failures."""

    pass


class GeminiServiceUnavailableError(GeminiError):
    """Raised when Gemini API is temporarily unavailable after retries."""

    def __init__(self, message: str, attempts: int = 0):
        self.attempts = attempts
        super().__init__(message)


def _is_retryable_error(error: Exception) -> bool:
    """Determine if an error is transient and worth retrying."""
    error_str = str(error).lower()

    # Check for known retryable keywords in the error message
    for keyword in _RETRYABLE_ERROR_KEYWORDS:
        if keyword in error_str:
            return True

    # Check for HTTP status code attributes (google-genai errors often have these)
    status_code = getattr(error, "status_code", None) or getattr(error, "code", None)
    if status_code and int(status_code) in _RETRYABLE_STATUS_CODES:
        return True

    # ConnectionError, TimeoutError are always retryable
    if isinstance(error, (ConnectionError, TimeoutError, OSError)):
        return True

    return False


SYSTEM_PROMPT = """You are Kevin, a friendly and helpful household finance assistant. Your primary purpose is helping users manage their financial records (expenses, income, assets, liabilities) AND answering general personal finance questions.

Personality & conversation style:
- Be warm, concise, and approachable.
- Respond naturally to greetings and casual conversation (e.g. "hi" → "Hey! How can I help with your finances today?").
- If the user asks something completely unrelated to finances or household budgeting (e.g. coding questions, weather, trivia), politely steer them back: "I'm best at helping with your household finances! Is there anything budget-related I can help you with?"
- Never give a cold rejection. Always be conversational and offer to help with what you can do.

Financial calculations & projections:
- You CAN and SHOULD help with any math-based financial question: loan amortization, payoff projections, savings goals, interest calculations, debt snowball/avalanche comparisons, mortgage estimates, budgeting scenarios, etc.
- Work through the math step by step and show the result clearly.

When the user asks to add, remove, or modify records, use the available tools. When they ask about their financial overview, use get_overview.

Important rules:
- The user's current financial overview (balances, expenses, income, assets, liabilities) is automatically included in the [Context] block of each message. USE this data directly in your answers — do NOT ask the user for amounts, balances, or payment figures that are already visible in the context. Only ask for information not present in the context (e.g. interest rates, future plans, external details).
- Always confirm what you did after executing an action.
- If the user doesn't specify month/year, use the provided current month and year from context.
- If the user doesn't specify a household, use list_households first to find available ones. If they only have one household, use that one automatically.
- When operating across all households, call the relevant tool once per household.
- Amounts should be positive numbers.
- The household_id is required for all operations except list_households.
- When searching records, you can filter by title text, by amount (exact or range), or both. For example, to find all records of exactly 600, set amount_min=600 and amount_max=600. To find records over 1000, set amount_min=1000. To find records under 500, set amount_max=500.
- When the user asks to modify, update, change, or adjust an existing record, use the update tools. First search for the record to get its ID, then use the appropriate update tool.
- When the user says "add $X to" an existing record, they mean increase the amount by $X. Search for the record, calculate the new amount (old + X), and use the update tool.
- When the user asks comparative or analytical questions (e.g. "which month had the biggest salary?", "what was my highest expense?", "compare my rent across months"), use search_records to retrieve all relevant records, then ANALYZE the results yourself. Compare amounts, find the maximum/minimum, calculate totals, identify trends, and provide a clear answer. You ARE capable of comparing and analyzing the data returned by search tools.
- You can perform arithmetic on search results: sums, averages, differences, percentages, finding max/min, sorting, and grouping by month/year/category.
"""

TOOL_DECLARATIONS = [
    types.FunctionDeclaration(
        name="list_households",
        description="List all households the user has access to. Call this first if you need to know which households are available.",
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={},
        ),
    ),
    types.FunctionDeclaration(
        name="add_expense",
        description="Add a new expense record to a household budget",
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={
                "household_id": types.Schema(
                    type=types.Type.INTEGER,
                    description="The household ID to add the expense to",
                ),
                "month": types.Schema(
                    type=types.Type.INTEGER, description="Month (1-12)"
                ),
                "year": types.Schema(
                    type=types.Type.INTEGER, description="Year (e.g. 2025)"
                ),
                "title": types.Schema(
                    type=types.Type.STRING,
                    description="Name/description of the expense",
                ),
                "amount": types.Schema(
                    type=types.Type.NUMBER, description="Amount spent"
                ),
            },
            required=["household_id", "month", "year", "title", "amount"],
        ),
    ),
    types.FunctionDeclaration(
        name="remove_expense",
        description="Remove an expense record by its ID",
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={
                "household_id": types.Schema(
                    type=types.Type.INTEGER, description="The household ID"
                ),
                "expense_id": types.Schema(
                    type=types.Type.INTEGER, description="The expense ID to remove"
                ),
                "month": types.Schema(
                    type=types.Type.INTEGER, description="Month (1-12)"
                ),
                "year": types.Schema(
                    type=types.Type.INTEGER, description="Year (e.g. 2025)"
                ),
            },
            required=["household_id", "expense_id", "month", "year"],
        ),
    ),
    types.FunctionDeclaration(
        name="update_expense",
        description="Update an existing expense record. Use this to modify the title and/or amount of an expense. First search for the record to get its ID.",
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={
                "household_id": types.Schema(
                    type=types.Type.INTEGER, description="The household ID"
                ),
                "expense_id": types.Schema(
                    type=types.Type.INTEGER, description="The expense ID to update"
                ),
                "month": types.Schema(
                    type=types.Type.INTEGER, description="Month (1-12)"
                ),
                "year": types.Schema(
                    type=types.Type.INTEGER, description="Year (e.g. 2025)"
                ),
                "title": types.Schema(
                    type=types.Type.STRING,
                    description="New name/description of the expense",
                ),
                "amount": types.Schema(
                    type=types.Type.NUMBER, description="New amount for the expense"
                ),
            },
            required=["household_id", "expense_id", "month", "year", "title", "amount"],
        ),
    ),
    types.FunctionDeclaration(
        name="add_income",
        description="Add a new income record to a household budget",
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={
                "household_id": types.Schema(
                    type=types.Type.INTEGER,
                    description="The household ID to add income to",
                ),
                "month": types.Schema(
                    type=types.Type.INTEGER, description="Month (1-12)"
                ),
                "year": types.Schema(
                    type=types.Type.INTEGER, description="Year (e.g. 2025)"
                ),
                "title": types.Schema(
                    type=types.Type.STRING,
                    description="Source/description of the income",
                ),
                "amount": types.Schema(
                    type=types.Type.NUMBER, description="Amount received"
                ),
            },
            required=["household_id", "month", "year", "title", "amount"],
        ),
    ),
    types.FunctionDeclaration(
        name="remove_income",
        description="Remove an income record by its ID",
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={
                "household_id": types.Schema(
                    type=types.Type.INTEGER, description="The household ID"
                ),
                "income_id": types.Schema(
                    type=types.Type.INTEGER, description="The income ID to remove"
                ),
                "month": types.Schema(
                    type=types.Type.INTEGER, description="Month (1-12)"
                ),
                "year": types.Schema(
                    type=types.Type.INTEGER, description="Year (e.g. 2025)"
                ),
            },
            required=["household_id", "income_id", "month", "year"],
        ),
    ),
    types.FunctionDeclaration(
        name="update_income",
        description="Update an existing income record. Use this to modify the title and/or amount of an income. First search for the record to get its ID.",
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={
                "household_id": types.Schema(
                    type=types.Type.INTEGER, description="The household ID"
                ),
                "income_id": types.Schema(
                    type=types.Type.INTEGER, description="The income ID to update"
                ),
                "month": types.Schema(
                    type=types.Type.INTEGER, description="Month (1-12)"
                ),
                "year": types.Schema(
                    type=types.Type.INTEGER, description="Year (e.g. 2025)"
                ),
                "title": types.Schema(
                    type=types.Type.STRING,
                    description="New source/description of the income",
                ),
                "amount": types.Schema(
                    type=types.Type.NUMBER, description="New amount for the income"
                ),
            },
            required=["household_id", "income_id", "month", "year", "title", "amount"],
        ),
    ),
    types.FunctionDeclaration(
        name="add_asset",
        description="Add a new asset record (investment, property, etc.)",
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={
                "household_id": types.Schema(
                    type=types.Type.INTEGER,
                    description="The household ID to add the asset to",
                ),
                "month": types.Schema(
                    type=types.Type.INTEGER, description="Month (1-12)"
                ),
                "year": types.Schema(
                    type=types.Type.INTEGER, description="Year (e.g. 2025)"
                ),
                "title": types.Schema(
                    type=types.Type.STRING, description="Name of the asset"
                ),
                "ticker": types.Schema(
                    type=types.Type.STRING, description="Stock ticker symbol (optional)"
                ),
                "amount": types.Schema(
                    type=types.Type.NUMBER, description="Quantity/units held"
                ),
                "bought_price": types.Schema(
                    type=types.Type.NUMBER, description="Price per unit when bought"
                ),
                "current_price": types.Schema(
                    type=types.Type.NUMBER, description="Current price per unit"
                ),
            },
            required=["household_id", "month", "year", "title"],
        ),
    ),
    types.FunctionDeclaration(
        name="remove_asset",
        description="Remove an asset record by its ID",
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={
                "household_id": types.Schema(
                    type=types.Type.INTEGER, description="The household ID"
                ),
                "asset_id": types.Schema(
                    type=types.Type.INTEGER, description="The asset ID to remove"
                ),
                "month": types.Schema(
                    type=types.Type.INTEGER, description="Month (1-12)"
                ),
                "year": types.Schema(
                    type=types.Type.INTEGER, description="Year (e.g. 2025)"
                ),
            },
            required=["household_id", "asset_id", "month", "year"],
        ),
    ),
    types.FunctionDeclaration(
        name="update_asset",
        description="Update an existing asset record. Use this to modify the title, ticker, amount, bought_price, or current_price of an asset. First search for the record to get its ID.",
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={
                "household_id": types.Schema(
                    type=types.Type.INTEGER, description="The household ID"
                ),
                "asset_id": types.Schema(
                    type=types.Type.INTEGER, description="The asset ID to update"
                ),
                "month": types.Schema(
                    type=types.Type.INTEGER, description="Month (1-12)"
                ),
                "year": types.Schema(
                    type=types.Type.INTEGER, description="Year (e.g. 2025)"
                ),
                "title": types.Schema(
                    type=types.Type.STRING, description="New name of the asset"
                ),
                "ticker": types.Schema(
                    type=types.Type.STRING, description="Stock ticker symbol (optional)"
                ),
                "amount": types.Schema(
                    type=types.Type.NUMBER, description="New quantity/units held"
                ),
                "bought_price": types.Schema(
                    type=types.Type.NUMBER, description="New price per unit when bought"
                ),
                "current_price": types.Schema(
                    type=types.Type.NUMBER, description="New current price per unit"
                ),
            },
            required=["household_id", "asset_id", "month", "year", "title"],
        ),
    ),
    types.FunctionDeclaration(
        name="add_liability",
        description="Add a new liability/debt record",
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={
                "household_id": types.Schema(
                    type=types.Type.INTEGER,
                    description="The household ID to add the liability to",
                ),
                "month": types.Schema(
                    type=types.Type.INTEGER, description="Month (1-12)"
                ),
                "year": types.Schema(
                    type=types.Type.INTEGER, description="Year (e.g. 2025)"
                ),
                "title": types.Schema(
                    type=types.Type.STRING,
                    description="Name/description of the liability",
                ),
                "amount": types.Schema(
                    type=types.Type.NUMBER, description="Amount owed"
                ),
            },
            required=["household_id", "month", "year", "title", "amount"],
        ),
    ),
    types.FunctionDeclaration(
        name="remove_liability",
        description="Remove a liability record by its ID",
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={
                "household_id": types.Schema(
                    type=types.Type.INTEGER, description="The household ID"
                ),
                "liability_id": types.Schema(
                    type=types.Type.INTEGER, description="The liability ID to remove"
                ),
                "month": types.Schema(
                    type=types.Type.INTEGER, description="Month (1-12)"
                ),
                "year": types.Schema(
                    type=types.Type.INTEGER, description="Year (e.g. 2025)"
                ),
            },
            required=["household_id", "liability_id", "month", "year"],
        ),
    ),
    types.FunctionDeclaration(
        name="update_liability",
        description="Update an existing liability record. Use this to modify the title and/or amount of a liability. First search for the record to get its ID.",
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={
                "household_id": types.Schema(
                    type=types.Type.INTEGER, description="The household ID"
                ),
                "liability_id": types.Schema(
                    type=types.Type.INTEGER, description="The liability ID to update"
                ),
                "month": types.Schema(
                    type=types.Type.INTEGER, description="Month (1-12)"
                ),
                "year": types.Schema(
                    type=types.Type.INTEGER, description="Year (e.g. 2025)"
                ),
                "title": types.Schema(
                    type=types.Type.STRING,
                    description="New name/description of the liability",
                ),
                "amount": types.Schema(
                    type=types.Type.NUMBER, description="New amount owed"
                ),
            },
            required=[
                "household_id",
                "liability_id",
                "month",
                "year",
                "title",
                "amount",
            ],
        ),
    ),
    types.FunctionDeclaration(
        name="get_overview",
        description="Get a financial overview/summary for a specific household, month or year",
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={
                "household_id": types.Schema(
                    type=types.Type.INTEGER,
                    description="The household ID to get overview for",
                ),
                "year": types.Schema(
                    type=types.Type.INTEGER, description="Year to query"
                ),
                "month": types.Schema(
                    type=types.Type.INTEGER,
                    description="Month to query (optional, omit for yearly overview)",
                ),
            },
            required=["household_id", "year"],
        ),
    ),
    types.FunctionDeclaration(
        name="search_records",
        description="Search for financial records (expenses, income, assets, liabilities) by title/name and/or amount across all or a specific household. Use this when the user asks to find, look up, or search for records. Supports filtering by exact amount (set both min and max to the same value), amount range, or text query, or any combination.",
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={
                "query": types.Schema(
                    type=types.Type.STRING,
                    description="Optional: search term to match against record titles (case-insensitive partial match). Can be omitted if searching by amount only.",
                ),
                "record_type": types.Schema(
                    type=types.Type.STRING,
                    description="Type of record to search: 'expense', 'income', 'asset', 'liability', or 'all'",
                ),
                "household_id": types.Schema(
                    type=types.Type.INTEGER,
                    description="Optional: limit search to a specific household. Omit to search all households.",
                ),
                "year": types.Schema(
                    type=types.Type.INTEGER,
                    description="Optional: limit search to a specific year",
                ),
                "month": types.Schema(
                    type=types.Type.INTEGER,
                    description="Optional: limit search to a specific month",
                ),
                "amount_min": types.Schema(
                    type=types.Type.NUMBER,
                    description="Optional: minimum amount (inclusive). For exact amount match, set both amount_min and amount_max to the same value.",
                ),
                "amount_max": types.Schema(
                    type=types.Type.NUMBER,
                    description="Optional: maximum amount (inclusive). For exact amount match, set both amount_min and amount_max to the same value.",
                ),
            },
            required=["record_type"],
        ),
    ),
]


class GeminiService:
    """
    User-scoped Gemini AI service. Can operate across all households the user belongs to.

    Usage:
        service = GeminiService(session=..., user_id=..., year=..., month=...)
        response_text, actions = service.chat(message, history)
    """

    def __init__(
        self,
        session: Session,
        user_id: int,
        year: int,
        month: int,
    ) -> None:
        if not settings.gemini_api_key:
            raise GeminiError("GEMINI_API_KEY is not configured")

        self.client = genai.Client(api_key=settings.gemini_api_key)
        self.model = "gemini-2.5-flash"
        self.user_id = user_id
        self.year = year
        self.month = month
        self.session = session

        # Repositories
        self.household_repo = HouseholdRepository(session)
        self.user_household_repo = UserHouseholdRepository(session)

        expense_repo = ExpenseRepository(session)
        income_repo = IncomeRepository(session)
        asset_repo = AssetRepository(session)
        liability_repo = LiabilityRepository(session)

        self.expense_service = ExpenseService(expense_repo)
        self.income_service = IncomeService(income_repo)
        self.asset_service = AssetService(asset_repo)
        self.liability_service = LiabilityService(liability_repo)
        self.overview_service = OverviewService(
            expense_repo, income_repo, asset_repo, liability_repo
        )

    def _verify_household_access(self, household_id: int) -> None:
        """Verify the user has access to the given household."""
        if not self.user_household_repo.exists(self.user_id, household_id):
            raise PermissionError(f"You don't have access to household {household_id}")

    def _generate_with_retry(
        self,
        contents: list[types.Content],
        config: types.GenerateContentConfig,
    ) -> Any:
        """Call Gemini's generate_content with retry logic for transient errors."""
        last_error: Exception | None = None

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=contents,
                    config=config,
                )
                return response
            except Exception as e:
                last_error = e
                if not _is_retryable_error(e) or attempt == MAX_RETRIES:
                    break
                delay = min(RETRY_BASE_DELAY * (2 ** (attempt - 1)), RETRY_MAX_DELAY)
                logger.warning(
                    "Gemini API call failed (attempt %d/%d): %s. Retrying in %.1fs...",
                    attempt,
                    MAX_RETRIES,
                    str(e),
                    delay,
                )
                time.sleep(delay)

        # All retries exhausted or non-retryable error
        assert last_error is not None
        if _is_retryable_error(last_error):
            raise GeminiServiceUnavailableError(
                f"AI service is temporarily unavailable after {MAX_RETRIES} attempts. "
                f"Please try again in a few moments. (Error: {last_error})",
                attempts=MAX_RETRIES,
            )
        raise last_error

    def chat(
        self,
        message: str,
        history: list[Any],
    ) -> tuple[str, list[dict[str, Any]]]:
        """
        Send a message to Gemini, handle function calls, return final response.

        Args:
            message: The user's message
            history: List of ChatMessage objects with .role and .content

        Returns:
            Tuple of (response_text, actions_list)
            where actions_list is [{"action": str, "success": bool, "detail": str}, ...]
        """
        try:
            contents = self._build_contents(message, history)
            actions: list[dict[str, Any]] = []

            tools = types.Tool(function_declarations=TOOL_DECLARATIONS)
            generate_config = types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                tools=[tools],
            )

            max_rounds = 10
            for _ in range(max_rounds):
                response = self._generate_with_retry(contents, generate_config)

                if not response.candidates:
                    raise GeminiError("No response from Gemini")

                candidate = response.candidates[0]
                function_calls = [
                    part for part in candidate.content.parts if part.function_call
                ]

                if not function_calls:
                    text_parts = [
                        part.text for part in candidate.content.parts if part.text
                    ]
                    return "".join(text_parts), actions

                # Process function calls
                contents.append(candidate.content)

                function_responses = []
                for part in function_calls:
                    fc = part.function_call
                    tool_name = fc.name
                    tool_args = dict(fc.args) if fc.args else {}

                    result = self._execute_tool(tool_name, tool_args)
                    actions.append(result)

                    function_responses.append(
                        types.Part.from_function_response(
                            name=tool_name,
                            response={
                                "result": result["detail"],
                                "success": result["success"],
                            },
                        )
                    )

                contents.append(types.Content(role="user", parts=function_responses))

            return (
                "I performed several actions but reached my processing limit. Please check your records.",
                actions,
            )

        except (GeminiError, GeminiServiceUnavailableError):
            raise
        except Exception as e:
            raise GeminiError(f"Failed to communicate with Gemini: {str(e)}")

    def _build_financial_context(self) -> str:
        """Pre-fetch the user's financial data to include in the message context."""
        lines = [f"[Context: current month={self.month}, current year={self.year}]"]

        try:
            households = self.household_repo.list_by_user(self.user_id)
            if households:
                lines.append(
                    f"[User households: {', '.join(f'{h.name} (id={h.id})' for h in households)}]"
                )
                for h in households:
                    try:
                        overview = self.overview_service.get_month(
                            h.id, self.year, self.month
                        )
                        data = _serialize_decimals(overview.model_dump())
                        lines.append(
                            f"[Financial overview for '{h.name}' ({self.month}/{self.year}): {data}]"
                        )
                    except Exception:
                        pass
        except Exception:
            pass

        return "\n".join(lines)

    def _build_contents(
        self,
        message: str,
        history: list[Any],
    ) -> list[types.Content]:
        contents: list[types.Content] = []

        for entry in history:
            role = "user" if entry.role == "user" else "model"
            contents.append(
                types.Content(
                    role=role, parts=[types.Part.from_text(text=entry.content)]
                )
            )

        context_prefix = self._build_financial_context() + "\n"
        contents.append(
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=context_prefix + message)],
            )
        )

        return contents

    def _execute_tool(self, tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
        """Execute a tool and return a standardized action result."""
        try:
            handler = getattr(self, f"_tool_{tool_name}", None)
            if not handler:
                return {
                    "action": tool_name,
                    "success": False,
                    "detail": f"Unknown tool: {tool_name}",
                }
            detail = handler(args)
            return {"action": tool_name, "success": True, "detail": detail}
        except PermissionError as e:
            return {"action": tool_name, "success": False, "detail": str(e)}
        except Exception as e:
            return {"action": tool_name, "success": False, "detail": str(e)}

    def _tool_list_households(self, args: dict[str, Any]) -> str:
        households = self.household_repo.list_by_user(self.user_id)
        if not households:
            return "You don't belong to any households yet."
        items = [f"- {h.name} (id={h.id})" for h in households]
        return "Your households:\n" + "\n".join(items)

    def _tool_add_expense(self, args: dict[str, Any]) -> str:
        household_id = int(args["household_id"])
        self._verify_household_access(household_id)
        expense = self.expense_service.create(
            household_id,
            int(args["year"]),
            int(args["month"]),
            args["title"],
            Decimal(str(args["amount"])),
        )
        return f"Added expense '{expense.title}' for {expense.amount}"

    def _tool_remove_expense(self, args: dict[str, Any]) -> str:
        household_id = int(args["household_id"])
        self._verify_household_access(household_id)
        self.expense_service.delete(
            int(args["expense_id"]),
            household_id,
            int(args["year"]),
            int(args["month"]),
        )
        return f"Removed expense #{args['expense_id']}"

    def _tool_update_expense(self, args: dict[str, Any]) -> str:
        household_id = int(args["household_id"])
        self._verify_household_access(household_id)
        expense = self.expense_service.update(
            int(args["expense_id"]),
            household_id,
            int(args["year"]),
            int(args["month"]),
            args["title"],
            Decimal(str(args["amount"])),
        )
        return f"Updated expense #{args['expense_id']} to '{expense.title}' for {expense.amount}"

    def _tool_add_income(self, args: dict[str, Any]) -> str:
        household_id = int(args["household_id"])
        self._verify_household_access(household_id)
        income = self.income_service.create(
            household_id,
            int(args["year"]),
            int(args["month"]),
            args["title"],
            Decimal(str(args["amount"])),
        )
        return f"Added income '{income.title}' for {income.amount}"

    def _tool_remove_income(self, args: dict[str, Any]) -> str:
        household_id = int(args["household_id"])
        self._verify_household_access(household_id)
        self.income_service.delete(
            int(args["income_id"]),
            household_id,
            int(args["year"]),
            int(args["month"]),
        )
        return f"Removed income #{args['income_id']}"

    def _tool_update_income(self, args: dict[str, Any]) -> str:
        household_id = int(args["household_id"])
        self._verify_household_access(household_id)
        income = self.income_service.update(
            int(args["income_id"]),
            household_id,
            int(args["year"]),
            int(args["month"]),
            args["title"],
            Decimal(str(args["amount"])),
        )
        return f"Updated income #{args['income_id']} to '{income.title}' for {income.amount}"

    def _tool_add_asset(self, args: dict[str, Any]) -> str:
        household_id = int(args["household_id"])
        self._verify_household_access(household_id)
        asset = self.asset_service.create(
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

    def _tool_remove_asset(self, args: dict[str, Any]) -> str:
        household_id = int(args["household_id"])
        self._verify_household_access(household_id)
        self.asset_service.delete(
            int(args["asset_id"]),
            household_id,
            int(args["year"]),
            int(args["month"]),
        )
        return f"Removed asset #{args['asset_id']}"

    def _tool_update_asset(self, args: dict[str, Any]) -> str:
        household_id = int(args["household_id"])
        self._verify_household_access(household_id)
        asset = self.asset_service.update(
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

    def _tool_add_liability(self, args: dict[str, Any]) -> str:
        household_id = int(args["household_id"])
        self._verify_household_access(household_id)
        liability = self.liability_service.create(
            household_id,
            int(args["year"]),
            int(args["month"]),
            args["title"],
            Decimal(str(args["amount"])),
        )
        return f"Added liability '{liability.title}' for {liability.amount}"

    def _tool_remove_liability(self, args: dict[str, Any]) -> str:
        household_id = int(args["household_id"])
        self._verify_household_access(household_id)
        self.liability_service.delete(
            int(args["liability_id"]),
            household_id,
            int(args["year"]),
            int(args["month"]),
        )
        return f"Removed liability #{args['liability_id']}"

    def _tool_update_liability(self, args: dict[str, Any]) -> str:
        household_id = int(args["household_id"])
        self._verify_household_access(household_id)
        liability = self.liability_service.update(
            int(args["liability_id"]),
            household_id,
            int(args["year"]),
            int(args["month"]),
            args["title"],
            Decimal(str(args["amount"])),
        )
        return f"Updated liability #{args['liability_id']} to '{liability.title}' for {liability.amount}"

    def _tool_search_records(self, args: dict[str, Any]) -> str:
        query = args.get("query", "").lower().strip()
        record_type = args.get("record_type", "all")
        household_id = args.get("household_id")
        year = args.get("year")
        month = args.get("month")
        amount_min = args.get("amount_min")
        amount_max = args.get("amount_max")

        # Get accessible household IDs
        if household_id:
            self._verify_household_access(int(household_id))
            household_ids = [int(household_id)]
        else:
            memberships = self.session.exec(
                select(UserHousehold.household_id).where(
                    UserHousehold.user_id == self.user_id
                )
            ).all()
            household_ids = list(memberships)

        results: list[str] = []

        type_model_map: dict[str, type] = {
            "expense": Expense,
            "income": Income,
            "asset": Asset,
            "liability": Liability,
        }

        types_to_search = (
            [type_model_map[record_type]]
            if record_type != "all"
            else list(type_model_map.values())
        )

        for model in types_to_search:
            stmt = select(model).where(
                model.household_id.in_(household_ids),
            )
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

            records = self.session.exec(stmt).all()
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

    def _tool_get_overview(self, args: dict[str, Any]) -> str:
        household_id = int(args["household_id"])
        self._verify_household_access(household_id)
        year = int(args["year"])
        month = args.get("month")

        if month:
            overview = self.overview_service.get_month(household_id, year, int(month))
        else:
            overview = self.overview_service.get_year(household_id, year)

        data = overview.model_dump()
        data = _serialize_decimals(data)
        return str(data)


def _serialize_decimals(obj: Any) -> Any:
    """Recursively convert Decimal values to float for JSON compatibility."""
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, dict):
        return {k: _serialize_decimals(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_serialize_decimals(item) for item in obj]
    return obj
