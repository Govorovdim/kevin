from datetime import datetime, timezone
from decimal import Decimal
from typing import Annotated

from pydantic import PlainSerializer


def utcnow() -> datetime:
    """Return the current UTC datetime (timezone-aware)."""
    return datetime.now(timezone.utc)


# Decimal that serializes as a JSON number (float) instead of a string.
# Use in Pydantic response / domain schemas so the API returns numeric JSON values.
JsonDecimal = Annotated[Decimal, PlainSerializer(float, return_type=float)]
