from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def utc_now() -> datetime:
    """
    Liefert die aktuelle Zeit als timezone-aware UTC datetime.
    """
    return datetime.now(timezone.utc)


def datetime_to_storage(value: datetime) -> str:
    """
    Wandelt ein datetime in einen UTC-ISO-String für Storage um.
    """
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    else:
        value = value.astimezone(timezone.utc)

    return value.isoformat()


def datetime_from_storage(value: Any) -> datetime:
    """
    Wandelt einen Storage-Wert defensiv in ein timezone-aware UTC-datetime um.
    """
    if not value:
        return utc_now()

    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    parsed = datetime.fromisoformat(str(value))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)

    return parsed.astimezone(timezone.utc)