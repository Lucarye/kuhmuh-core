from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


def utc_now() -> datetime:
    """
    Liefert die aktuelle Zeit als timezone-aware UTC datetime.
    """
    return datetime.now(UTC)


def datetime_to_storage(value: datetime) -> str:
    """
    Wandelt ein datetime in einen UTC-ISO-String für Storage um.
    """
    value = value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)

    return value.isoformat()


def datetime_from_storage(value: Any) -> datetime:
    """
    Wandelt einen Storage-Wert defensiv in ein timezone-aware UTC-datetime um.
    """
    if not value:
        return utc_now()

    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    parsed = datetime.fromisoformat(str(value))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)

    return parsed.astimezone(UTC)
