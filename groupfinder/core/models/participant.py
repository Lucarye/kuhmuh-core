from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from ..utils.datetime_utils import datetime_to_storage, datetime_from_storage
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

    def to_dict(self) -> dict[str, Any]:
        """
        Serialisiert den Teilnehmer in eine JSON-kompatible Struktur.

        Zeitwerte werden immer als UTC-ISO-String gespeichert.
        """
        return {
            "user_id": self.user_id,
            "display_name": self.display_name,
            "joined_at": datetime_to_storage(self.joined_at),
            "extra_data": dict(self.extra_data),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Participant":
        """
        Deserialisiert einen Teilnehmer aus einer Storage-Struktur.

        Fehlende optionale Felder werden defensiv mit Defaults ergänzt.
        """
        return cls(
            user_id=int(data["user_id"]),
            display_name=str(data.get("display_name", "")),
            joined_at=datetime_from_storage(data.get("joined_at")),
            extra_data=dict(data.get("extra_data", {})),
        )

