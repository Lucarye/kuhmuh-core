from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(slots=True)
class Participant:
    """
    Repräsentiert einen Teilnehmer innerhalb einer Gruppensuche.

    Das Objekt bleibt bewusst generisch. Modul- oder spielbezogene Zusatzeinträge
    können über `extra_data` gehalten werden, ohne das Kernmodell auf ein Spiel
    oder einen Content-Typ festzunageln.
    """

    user_id: int
    display_name: str
    joined_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    extra_data: dict[str, Any] = field(default_factory=dict)

    def update_display_name(self, display_name: str) -> None:
        """Aktualisiert den Anzeigenamen des Teilnehmers."""
        self.display_name = display_name