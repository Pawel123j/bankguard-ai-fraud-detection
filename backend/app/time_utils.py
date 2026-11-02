from datetime import datetime, timezone
from typing import Any


def utc_naive(value: Any) -> datetime:
    """SQLite stores UTC without tzinfo; offset-free input explicitly means UTC."""
    parsed = value if isinstance(value, datetime) else datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    return parsed.replace(tzinfo=timezone.utc).replace(tzinfo=None) if parsed.tzinfo is None else parsed.astimezone(timezone.utc).replace(tzinfo=None)


def utc_iso(value: datetime) -> str:
    return utc_naive(value).isoformat() + "Z"


def utc_now_naive() -> datetime:
    """Return current UTC time without tzinfo for SQLite DateTime columns."""
    return datetime.now(timezone.utc).replace(tzinfo=None)
