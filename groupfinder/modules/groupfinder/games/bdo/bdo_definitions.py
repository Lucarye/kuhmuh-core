from __future__ import annotations

from ...definitions.base_definitions import ContentDefinition, FieldDefinition


BDO_CONTENT_DEFINITIONS: dict[str, ContentDefinition] = {
    "bdo_spot": ContentDefinition(
        content_key="bdo_spot",
        display_name="BDO Spot",
        description="Gruppensuche für einen Grind-Spot in Black Desert Online.",
        default_slots_total=5,
        fields=(
            FieldDefinition(
                key="spot_name",
                label="Spot",
                field_type="choice",
                required=True,
                choices=(
                    "Olun",
                    "Dehkia 1",
                    "Dehkia 2",
                    "Gyfin",
                ),
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
    "bdo_muhhelfer": ContentDefinition(
        content_key="bdo_muhhelfer",
        display_name="BDO Muhhelfer",
        description="Gruppensuche für Muhhelfer / Unterstützungsläufe in Black Desert Online.",
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