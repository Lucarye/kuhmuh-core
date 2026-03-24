from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True, frozen=True)
class FieldDefinition:
    """
    Beschreibt ein einzelnes Eingabefeld für einen Content-Typ.
    """

    key: str
    label: str
    field_type: str
    required: bool = True
    default: Any = None
    choices: tuple[str, ...] = field(default_factory=tuple)


@dataclass(slots=True, frozen=True)
class ContentDefinition:
    """
    Beschreibt einen verfügbaren Content-Typ innerhalb des Groupfinder-Moduls.
    """

    content_key: str
    display_name: str
    description: str
    default_slots_total: int
    fields: tuple[FieldDefinition, ...] = field(default_factory=tuple)


BASE_CONTENT_DEFINITIONS: dict[str, ContentDefinition] = {
    "generic_group": ContentDefinition(
        content_key="generic_group",
        display_name="Generische Gruppensuche",
        description="Ein generischer Gruppensuche-Eintrag ohne spielgebundene Speziallogik.",
        default_slots_total=5,
        fields=(
            FieldDefinition(
                key="title",
                label="Titel",
                field_type="string",
                required=True,
            ),
            FieldDefinition(
                key="description",
                label="Beschreibung",
                field_type="string",
                required=False,
                default="",
            ),
        ),
    ),
}