"""Gemini AI chat service."""

import logging
import time
from decimal import Decimal
from typing import Any

from google import genai
from google.genai import types
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
from kevin.services.income import IncomeService
from kevin.services.liability import LiabilityService
from kevin.services.overview import OverviewService
from kevin.settings import settings

from .exceptions import GeminiError, GeminiServiceUnavailableError
from .handlers import ToolHandlers
from .prompt import SYSTEM_PROMPT
from .tools import TOOL_DECLARATIONS

logger = logging.getLogger(__name__)

# Retry configuration
_MAX_RETRIES = 3
_RETRY_BASE_DELAY = 1.0  # seconds
_RETRY_MAX_DELAY = 8.0  # seconds

# Maximum tool-call rounds per chat turn (prevents infinite loops)
_MAX_TOOL_ROUNDS = 10

_RETRYABLE_STATUS_CODES = frozenset({429, 500, 502, 503, 504})
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


def _is_retryable_error(error: Exception) -> bool:
    """Determine if an error is transient and worth retrying."""
    error_str = str(error).lower()

    for keyword in _RETRYABLE_ERROR_KEYWORDS:
        if keyword in error_str:
            return True

    status_code = getattr(error, "status_code", None) or getattr(error, "code", None)
    if status_code and int(status_code) in _RETRYABLE_STATUS_CODES:
        return True

    if isinstance(error, (ConnectionError, TimeoutError, OSError)):
        return True

    return False


def _serialize_decimals(obj: Any) -> Any:
    """Recursively convert Decimal values to float for JSON compatibility."""
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, dict):
        return {k: _serialize_decimals(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_serialize_decimals(item) for item in obj]
    return obj


class GeminiService:
    """User-scoped Gemini AI chat service.

    Usage:
        service = GeminiService(session=session, user_id=1, year=2025, month=6)
        response_text, actions = service.chat("What are my expenses?", history=[])
    """

    def __init__(
        self,
        *,
        session: Session,
        user_id: int,
        year: int,
        month: int,
    ) -> None:
        if not settings.gemini_api_key:
            raise GeminiError("GEMINI_API_KEY is not configured")

        self._client = genai.Client(api_key=settings.gemini_api_key)
        self._model = settings.gemini_model
        self._user_id = user_id
        self._year = year
        self._month = month
        self._session = session

        # Set up repositories
        self._household_repo = HouseholdRepository(session)
        user_household_repo = UserHouseholdRepository(session)

        expense_repo = ExpenseRepository(session)
        income_repo = IncomeRepository(session)
        asset_repo = AssetRepository(session)
        liability_repo = LiabilityRepository(session)

        # Set up domain services
        overview_service = OverviewService(
            expense_repo, income_repo, asset_repo, liability_repo
        )
        self._overview_service = overview_service

        # Set up currency service (connection-pooled, cached)
        currency_service = CurrencyService()
        self._currency_service = currency_service

        # Set up tool handlers with all dependencies injected
        self._handlers = ToolHandlers(
            session=session,
            user_id=user_id,
            expense_service=ExpenseService(expense_repo),
            income_service=IncomeService(income_repo),
            asset_service=AssetService(asset_repo),
            liability_service=LiabilityService(liability_repo),
            overview_service=overview_service,
            currency_service=currency_service,
            user_household_repo=user_household_repo,
        )

    def chat(
        self,
        message: str,
        history: list[Any],
    ) -> tuple[str, list[dict[str, Any]]]:
        """Send a message and return the AI response with any actions taken.

        Args:
            message: The user's message text.
            history: List of previous ChatMessage objects with .role and .content.

        Returns:
            A tuple of (response_text, actions_list) where actions_list contains
            dicts with keys: action (str), success (bool), detail (str).

        Raises:
            GeminiServiceUnavailableError: If the API is unreachable after retries.
            GeminiError: For other AI service failures.
        """
        try:
            contents = self._build_contents(message, history)
            actions: list[dict[str, Any]] = []

            config = types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                tools=[types.Tool(function_declarations=TOOL_DECLARATIONS)],
            )

            for _ in range(_MAX_TOOL_ROUNDS):
                response = self._generate_with_retry(contents, config)

                if not response.candidates:
                    raise GeminiError("No response candidates returned by Gemini")

                candidate = response.candidates[0]
                function_calls = [
                    part for part in candidate.content.parts if part.function_call
                ]

                if not function_calls:
                    text_parts = [
                        part.text for part in candidate.content.parts if part.text
                    ]
                    return "".join(text_parts), actions

                contents.append(candidate.content)

                function_responses = []
                for part in function_calls:
                    fc = part.function_call
                    tool_name = fc.name
                    tool_args = dict(fc.args) if fc.args else {}

                    result = self._handlers.execute(tool_name, tool_args)
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

            # Exhausted tool-call rounds
            return (
                "I performed several actions but reached my processing limit. "
                "Please check your records.",
                actions,
            )

        except (GeminiError, GeminiServiceUnavailableError):
            raise
        except Exception as e:
            raise GeminiError(f"Failed to communicate with Gemini: {e}") from e

    # ------------------------------------------------------------------
    # Private: Gemini API interaction
    # ------------------------------------------------------------------

    def _generate_with_retry(
        self,
        contents: list[types.Content],
        config: types.GenerateContentConfig,
    ) -> Any:
        """Call Gemini's generate_content with exponential-backoff retry."""
        last_error: Exception | None = None

        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                return self._client.models.generate_content(
                    model=self._model,
                    contents=contents,
                    config=config,
                )
            except Exception as e:
                last_error = e
                if not _is_retryable_error(e) or attempt == _MAX_RETRIES:
                    break

                delay = min(_RETRY_BASE_DELAY * (2 ** (attempt - 1)), _RETRY_MAX_DELAY)
                logger.warning(
                    "Gemini API call failed (attempt %d/%d): %s. Retrying in %.1fs...",
                    attempt,
                    _MAX_RETRIES,
                    e,
                    delay,
                )
                time.sleep(delay)

        assert last_error is not None
        if _is_retryable_error(last_error):
            raise GeminiServiceUnavailableError(
                f"AI service unavailable after {_MAX_RETRIES} attempts: {last_error}",
                attempts=_MAX_RETRIES,
            )
        raise last_error

    # ------------------------------------------------------------------
    # Private: Context building
    # ------------------------------------------------------------------

    def _build_contents(
        self,
        message: str,
        history: list[Any],
    ) -> list[types.Content]:
        """Build the full conversation contents to send to Gemini.

        Includes conversation history and a context-enriched user message.
        """
        contents: list[types.Content] = []

        # Replay conversation history
        for entry in history:
            role = "user" if entry.role == "user" else "model"
            contents.append(
                types.Content(
                    role=role,
                    parts=[types.Part.from_text(text=entry.content)],
                )
            )

        # Append current message with financial context prefix
        context = self._build_financial_context()
        contents.append(
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=f"{context}\n{message}")],
            )
        )

        return contents

    def _build_financial_context(self) -> str:
        """Build a context string with the user's current financial state.

        This gives the AI immediate access to household info and balances
        without needing a tool call on every turn.
        """
        lines = [f"[Context: current month={self._month}, current year={self._year}]"]

        try:
            households = self._household_repo.list_by_user(self._user_id)
            if households:
                household_info = ", ".join(
                    f"{h.name} (id={h.id}, currency={h.currency})" for h in households
                )
                lines.append(f"[User households: {household_info}]")

                for h in households:
                    if h.id is None:
                        continue
                    try:
                        overview = self._overview_service.get_month(
                            h.id, self._year, self._month
                        )
                        data = _serialize_decimals(overview.model_dump())
                        lines.append(
                            f"[Financial overview for '{h.name}' "
                            f"({self._month}/{self._year}): {data}]"
                        )
                    except Exception:
                        pass
        except Exception:
            pass

        return "\n".join(lines)
