"""Shared schema types."""

from datetime import UTC, datetime
from typing import Annotated

from pydantic import BeforeValidator


def _ensure_utc(v: datetime | None) -> datetime | None:
    """Ensure datetime has UTC timezone for proper serialization."""
    if v and v.tzinfo is None:
        return v.replace(tzinfo=UTC)
    return v


UTCDateTime = Annotated[datetime, BeforeValidator(_ensure_utc)]
