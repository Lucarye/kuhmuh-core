from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..definitions.base_definitions import ContentDefinition


@dataclass(slots=True)
class ValidationResult:
    """
    Standardisierte Rückgabe für Modul-Validierungen.
    """

    valid: bool
    errors: list[str] = field(default_factory=list)
    normalized_payload: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def ok(cls, normalized_payload: dict[str, Any]) -> "ValidationResult":
        return cls(valid=True, errors=[], normalized_payload=normalized_payload)

    @classmethod
    def fail(cls, *errors: str) -> "ValidationResult":
        return cls(valid=False, errors=list(errors), normalized_payload={})


class BaseValidator:
    """
    Generischer Validator für ContentDefinition-basierte Payloads.
    """

    def validate_create_payload(
        self,
        *,
        content_definition: ContentDefinition,
        payload: dict[str, Any],
        slots_total: int,
    ) -> ValidationResult:
        """
        Prüft eine Create-Payload gegen eine ContentDefinition.
        """
        if slots_total < 1:
            return ValidationResult.fail("Die Gruppengröße muss mindestens 1 sein.")

        normalized_payload: dict[str, Any] = {}
        errors: list[str] = []

        for field_definition in content_definition.fields:
            value = payload.get(field_definition.key, field_definition.default)

            if field_definition.required and self._is_missing(value):
                errors.append(f"Pflichtfeld fehlt: {field_definition.label}")
                continue

            if value is None:
                normalized_payload[field_definition.key] = value
                continue

            if field_definition.field_type == "choice":
                if not isinstance(value, str):
                    errors.append(f"Ungültiger Typ für Feld: {field_definition.label}")
                    continue

                if value not in field_definition.choices:
                    errors.append(
                        f"Ungültige Auswahl für {field_definition.label}: {value}"
                    )
                    continue

            elif field_definition.field_type == "string":
                if not isinstance(value, str):
                    errors.append(f"Ungültiger Typ für Feld: {field_definition.label}")
                    continue

                value = value.strip()

                if field_definition.required and not value:
                    errors.append(f"Pflichtfeld fehlt: {field_definition.label}")
                    continue

            normalized_payload[field_definition.key] = value

        if errors:
            return ValidationResult.fail(*errors)

        return ValidationResult.ok(normalized_payload=normalized_payload)

    @staticmethod
    def _is_missing(value: Any) -> bool:
        """
        Prüft, ob ein Pflichtwert effektiv fehlt.
        """
        if value is None:
            return True

        if isinstance(value, str) and not value.strip():
            return True

        return False