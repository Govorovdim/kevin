"""Currency conversion service using the Frankfurter API."""

import logging
import time
from dataclasses import dataclass
from typing import Self

import httpx

from kevin.settings import settings

logger = logging.getLogger(__name__)

# Defaults
_DEFAULT_TIMEOUT = 10.0
_DEFAULT_CACHE_TTL = 300  # 5 minutes
_MAX_RETRIES = 3
_RETRY_BASE_DELAY = 0.5  # seconds
_RETRY_MAX_DELAY = 4.0  # seconds
_RETRYABLE_STATUS_CODES = frozenset({429, 500, 502, 503, 504})


class CurrencyError(Exception):
    """Base error for currency service failures."""


class UnsupportedCurrencyError(CurrencyError):
    """Raised when a currency pair is not supported."""

    def __init__(self, from_currency: str, to_currency: str) -> None:
        self.from_currency = from_currency
        self.to_currency = to_currency
        super().__init__(
            f"Unsupported currency pair: {from_currency} → {to_currency}. "
            "Supported currencies include USD, EUR, GBP, JPY, CHF, CAD, AUD, "
            "SEK, NOK, DKK, PLN, CZK, HUF, RON, BGN, TRY, BRL, CNY, KRW, etc."
        )


class CurrencyServiceUnavailableError(CurrencyError):
    """Raised when the exchange rate API is unreachable after retries."""

    def __init__(self, attempts: int) -> None:
        self.attempts = attempts
        super().__init__(
            f"Currency conversion service unavailable after {attempts} attempts. "
            "Please try again later."
        )


@dataclass(frozen=True, slots=True)
class ConversionResult:
    """Immutable result of a currency conversion."""

    amount: float
    from_currency: str
    to_currency: str
    converted_amount: float
    rate: float
    date: str  # The date of the exchange rate (ISO format)

    def __str__(self) -> str:
        return (
            f"{self.amount} {self.from_currency} = "
            f"{self.converted_amount:.2f} {self.to_currency} "
            f"(rate: 1 {self.from_currency} = {self.rate:.4f} {self.to_currency}, "
            f"as of {self.date})"
        )


@dataclass(slots=True)
class _CacheEntry:
    """Internal cache entry with expiration."""

    result: ConversionResult
    expires_at: float


class CurrencyService:
    """Converts currencies using live exchange rates from Frankfurter API.

    Usage:
        service = CurrencyService()
        result = service.convert(100, "USD", "EUR")
        print(result)  # 100 USD = 92.15 EUR (rate: 1 USD = 0.9215 EUR, as of 2025-06-05)

    As a context manager:
        with CurrencyService() as service:
            result = service.convert(100, "USD", "EUR")
    """

    def __init__(
        self,
        *,
        base_url: str | None = None,
        timeout: float = _DEFAULT_TIMEOUT,
        cache_ttl: float = _DEFAULT_CACHE_TTL,
        max_retries: int = _MAX_RETRIES,
    ) -> None:
        self._base_url = (base_url or settings.currency_api_url).rstrip("/")
        self._timeout = timeout
        self._cache_ttl = cache_ttl
        self._max_retries = max_retries
        self._cache: dict[str, _CacheEntry] = {}

        self._client = httpx.Client(
            base_url=self._base_url,
            timeout=timeout,
            follow_redirects=True,
            headers={"Accept": "application/json"},
        )

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def close(self) -> None:
        """Close the underlying HTTP client and release connections."""
        self._client.close()

    def convert(
        self, amount: float, from_currency: str, to_currency: str
    ) -> ConversionResult:
        """Convert an amount between two currencies.

        Args:
            amount: The amount to convert (must be positive).
            from_currency: ISO 4217 currency code (e.g. "USD").
            to_currency: ISO 4217 currency code (e.g. "EUR").

        Returns:
            ConversionResult with the converted amount and rate info.

        Raises:
            ValueError: If amount is not positive or currency codes are invalid.
            UnsupportedCurrencyError: If the currency pair is not supported.
            CurrencyServiceUnavailableError: If the API is unreachable.
            CurrencyError: For other unexpected failures.
        """
        from_currency = self._validate_currency_code(from_currency, "from_currency")
        to_currency = self._validate_currency_code(to_currency, "to_currency")

        if amount <= 0:
            raise ValueError(f"Amount must be positive, got {amount}")

        if from_currency == to_currency:
            return ConversionResult(
                amount=amount,
                from_currency=from_currency,
                to_currency=to_currency,
                converted_amount=amount,
                rate=1.0,
                date="N/A",
            )

        # Check cache for the rate (cache is per-pair, amount-independent)
        cache_key = f"{from_currency}:{to_currency}"
        cached = self._get_cached_rate(cache_key)
        if cached is not None:
            converted = round(amount * cached.rate, 2)
            return ConversionResult(
                amount=amount,
                from_currency=from_currency,
                to_currency=to_currency,
                converted_amount=converted,
                rate=cached.rate,
                date=cached.date,
            )

        # Fetch from API
        data = self._fetch_rate(from_currency, to_currency)

        rate = data["rates"][to_currency] / data["amount"]
        converted_amount = round(amount * rate, 2)
        date = data.get("date", "unknown")

        result = ConversionResult(
            amount=amount,
            from_currency=from_currency,
            to_currency=to_currency,
            converted_amount=converted_amount,
            rate=rate,
            date=date,
        )

        # Cache the rate (not the amount-specific result)
        self._set_cache(
            cache_key,
            ConversionResult(
                amount=1.0,
                from_currency=from_currency,
                to_currency=to_currency,
                converted_amount=rate,
                rate=rate,
                date=date,
            ),
        )

        return result

    def get_rate(self, from_currency: str, to_currency: str) -> float:
        """Get the current exchange rate between two currencies.

        Convenience method that returns just the rate as a float.
        """
        result = self.convert(1.0, from_currency, to_currency)
        return result.rate

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_currency_code(code: str, param_name: str) -> str:
        """Validate and normalize a currency code."""
        code = code.strip().upper()
        if len(code) != 3 or not code.isalpha():
            raise ValueError(
                f"Invalid {param_name}: '{code}'. "
                "Currency code must be a 3-letter ISO 4217 code (e.g. USD, EUR)."
            )
        return code

    def _get_cached_rate(self, key: str) -> ConversionResult | None:
        """Return cached result if still valid, otherwise evict and return None."""
        entry = self._cache.get(key)
        if entry is None:
            return None
        if time.monotonic() > entry.expires_at:
            del self._cache[key]
            return None
        return entry.result

    def _set_cache(self, key: str, result: ConversionResult) -> None:
        """Store a conversion result in cache with TTL."""
        self._cache[key] = _CacheEntry(
            result=result,
            expires_at=time.monotonic() + self._cache_ttl,
        )

    def _fetch_rate(self, from_currency: str, to_currency: str) -> dict:
        """Fetch exchange rate from the API with retry logic.

        Returns the raw JSON response dict on success.

        Raises:
            UnsupportedCurrencyError: On 404/422 (invalid pair).
            CurrencyServiceUnavailableError: After all retries exhausted.
            CurrencyError: On unexpected non-retryable errors.
        """
        last_error: Exception | None = None

        for attempt in range(1, self._max_retries + 1):
            try:
                response = self._client.get(
                    "/latest",
                    params={
                        "from": from_currency,
                        "to": to_currency,
                        "amount": 1,
                    },
                )

                if response.status_code in (404, 422):
                    raise UnsupportedCurrencyError(from_currency, to_currency)

                response.raise_for_status()

                data = response.json()
                if to_currency not in data.get("rates", {}):
                    raise UnsupportedCurrencyError(from_currency, to_currency)

                return data

            except (UnsupportedCurrencyError, ValueError):
                # Non-retryable errors — propagate immediately
                raise

            except httpx.HTTPStatusError as e:
                last_error = e
                if e.response.status_code not in _RETRYABLE_STATUS_CODES:
                    raise CurrencyError(
                        f"Exchange rate API returned {e.response.status_code}"
                    ) from e

            except httpx.TimeoutException as e:
                last_error = e

            except httpx.HTTPError as e:
                last_error = e

            except Exception as e:
                # Unexpected error — don't retry
                raise CurrencyError(
                    f"Unexpected error fetching exchange rate: {e}"
                ) from e

            # Retry with exponential backoff
            if attempt < self._max_retries:
                delay = min(
                    _RETRY_BASE_DELAY * (2 ** (attempt - 1)),
                    _RETRY_MAX_DELAY,
                )
                logger.warning(
                    "Currency API request failed (attempt %d/%d): %s. "
                    "Retrying in %.1fs...",
                    attempt,
                    self._max_retries,
                    last_error,
                    delay,
                )
                time.sleep(delay)

        # All retries exhausted
        logger.error(
            "Currency API unavailable after %d attempts. Last error: %s",
            self._max_retries,
            last_error,
        )
        raise CurrencyServiceUnavailableError(attempts=self._max_retries)
