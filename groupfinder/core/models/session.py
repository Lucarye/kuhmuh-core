from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from ..utils.datetime_utils import datetime_from_storage, datetime_to_storage, utc_now


@dataclass(slots=True)
class FlowSession:
    """
    Temporärer Zustandscontainer für Create- und Edit-Flows.

    Die Session hält bewusst nur Flow- und Payload-Daten.
    Discord-spezifische Objekte oder UI-Zustände gehören nicht in dieses Modell.
    """

    user_id: int
    guild_id: int
    mode: str
    module_key: str

    current_step: str
    payload: dict[str, Any] = field(default_factory=dict)

    created_at: datetime = field(default_factory=utc_now)
    expires_at: datetime = field(
        default_factory=lambda: utc_now() + timedelta(minutes=15)
    )

    def is_expired(self, now: datetime | None = None) -> bool:
        """Prüft, ob die Session bereits abgelaufen ist."""
        now = now or utc_now()
        return now >= self.expires_at

    def set_step(self, step: str) -> None:
        """Aktualisiert den aktuellen Flow-Schritt."""
        self.current_step = step

    def update_payload(self, **values: Any) -> None:
        """Ergänzt oder überschreibt Werte im Session-Payload."""
        self.payload.update(values)

    def extend(self, minutes: int = 15) -> None:
        """Verlängert die Session ab jetzt um die angegebene Anzahl Minuten."""
        self.expires_at = utc_now() + timedelta(minutes=minutes)

    def to_dict(self) -> dict[str, Any]:
        """
        Serialisiert die Flow-Session in eine JSON-kompatible Storage-Struktur.

        Zeitwerte werden immer als UTC-ISO-String gespeichert.
        """
        return {
            "user_id": self.user_id,
            "guild_id": self.guild_id,
            "mode": self.mode,
            "module_key": self.module_key,
            "current_step": self.current_step,
            "payload": dict(self.payload),
            "created_at": datetime_to_storage(self.created_at),
            "expires_at": datetime_to_storage(self.expires_at),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FlowSession":
        """
        Deserialisiert eine Flow-Session aus einer Storage-Struktur.

        Fehlende optionale Felder werden defensiv mit Defaults ergänzt.
        """
        return cls(
            user_id=int(data["user_id"]),
            guild_id=int(data.get("guild_id", 0)),
            mode=str(data.get("mode", "")),
            module_key=str(data.get("module_key", "")),
            current_step=str(data.get("current_step", "")),
            payload=dict(data.get("payload", {})),
            created_at=datetime_from_storage(data.get("created_at")),
            expires_at=datetime_from_storage(data.get("expires_at")),
        )