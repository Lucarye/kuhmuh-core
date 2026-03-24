from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .search import Search


@dataclass(slots=True)
class OperationResult:
    """
    Einheitliche Rückgabe für Core-Aktionen.

    Dadurch können Command-, UI- und spätere Dispatch-Schichten mit einem
    konsistenten Ergebnis arbeiten, ohne den internen Ablauf einer Aktion
    kennen zu müssen.
    """

    success: bool
    changed: bool = False

    user_message: str | None = None
    admin_message: str | None = None
    error_code: str | None = None

    dispatch_required: bool = False
    search: Search | None = None

    extra: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def ok(
        cls,
        *,
        changed: bool = False,
        user_message: str | None = None,
        admin_message: str | None = None,
        dispatch_required: bool = False,
        search: Search | None = None,
        extra: dict[str, Any] | None = None,
    ) -> "OperationResult":
        """Erzeugt ein erfolgreiches OperationResult."""
        return cls(
            success=True,
            changed=changed,
            user_message=user_message,
            admin_message=admin_message,
            dispatch_required=dispatch_required,
            search=search,
            extra=extra or {},
        )

    @classmethod
    def fail(
        cls,
        *,
        user_message: str | None = None,
        admin_message: str | None = None,
        error_code: str | None = None,
        search: Search | None = None,
        extra: dict[str, Any] | None = None,
    ) -> "OperationResult":
        """Erzeugt ein fehlgeschlagenes OperationResult."""
        return cls(
            success=False,
            changed=False,
            user_message=user_message,
            admin_message=admin_message,
            error_code=error_code,
            dispatch_required=False,
            search=search,
            extra=extra or {},
        )