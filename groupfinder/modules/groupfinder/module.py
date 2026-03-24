from __future__ import annotations

from typing import Any

from .definitions.base_definitions import BASE_CONTENT_DEFINITIONS, ContentDefinition
from .games.bdo.bdo_definitions import BDO_CONTENT_DEFINITIONS
from .validators.base_validator import BaseValidator, ValidationResult


class GroupFinderModule:
    """
    Fachlicher Einstiegspunkt für das Groupfinder-Modul.

    Das Modul bündelt Content-Definitionen, Validierung und erste
    fachliche Display-Hilfen. Der Core arbeitet nur gegen diese
    öffentliche Moduloberfläche, nicht gegen einzelne Definitionsdateien.
    """

    module_key = "groupfinder"

    def __init__(self) -> None:
        self._validator = BaseValidator()
        self._content_definitions: dict[str, ContentDefinition] = {
            **BASE_CONTENT_DEFINITIONS,
            **BDO_CONTENT_DEFINITIONS,
        }

    def list_content_definitions(self) -> list[ContentDefinition]:
        """
        Gibt alle verfügbaren Content-Definitionen zurück.
        """
        return list(self._content_definitions.values())

    def get_content_definition(self, content_key: str) -> ContentDefinition | None:
        """
        Gibt die Content-Definition für einen Schlüssel zurück.
        """
        return self._content_definitions.get(content_key)

    def validate_create_payload(
        self,
        *,
        content_key: str,
        payload: dict[str, Any],
        slots_total: int,
    ) -> ValidationResult:
        """
        Validiert eine Create-Payload für den angegebenen Content-Typ.
        """
        content_definition = self.get_content_definition(content_key)
        if content_definition is None:
            return ValidationResult.fail(
                f"Unbekannter Content-Typ: {content_key}"
            )

        return self._validator.validate_create_payload(
            content_definition=content_definition,
            payload=payload,
            slots_total=slots_total,
        )

    def build_display_data(self, *, content_key: str, payload: dict[str, Any]) -> dict[str, Any]:
        """
        Liefert strukturierte Anzeigedaten für Renderer.

        Diese Methode baut noch keine Embeds, sondern nur eine neutrale
        Datenrepräsentation für die UI-Schicht.
        """
        content_definition = self.get_content_definition(content_key)
        if content_definition is None:
            return {
                "title": "Unbekannter Inhalt",
                "subtitle": "",
                "lines": [],
            }

        lines: list[str] = []

        for field_definition in content_definition.fields:
            value = payload.get(field_definition.key)
            if value is None or value == "":
                continue

            lines.append(f"{field_definition.label}: {value}")

        return {
            "title": content_definition.display_name,
            "subtitle": content_definition.description,
            "lines": lines,
        }