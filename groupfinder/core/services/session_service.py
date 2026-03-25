from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any


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

    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc) + timedelta(minutes=15)
    )

    def is_expired(self, now: datetime | None = None) -> bool:
        """Prüft, ob die Session bereits abgelaufen ist."""
        now = now or datetime.now(timezone.utc)
        return now >= self.expires_at

    def set_step(self, step: str) -> None:
        """Aktualisiert den aktuellen Flow-Schritt."""
        self.current_step = step

    def update_payload(self, **values: Any) -> None:
        """Ergänzt oder überschreibt Werte im Session-Payload."""
        self.payload.update(values)

    def extend(self, minutes: int = 15) -> None:
        """Verlängert die Session ab jetzt um die angegebene Anzahl Minuten."""
        self.expires_at = datetime.now(timezone.utc) + timedelta(minutes=minutes)

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
            "created_at": self._datetime_to_storage(self.created_at),
            "expires_at": self._datetime_to_storage(self.expires_at),
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
            created_at=cls._datetime_from_storage(data.get("created_at")),
            expires_at=cls._datetime_from_storage(data.get("expires_at")),
        )

    @staticmethod
    def _datetime_to_storage(value: datetime) -> str:
        """
        Wandelt ein datetime in einen UTC-ISO-String für Storage um.
        """
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        else:
            value = value.astimezone(timezone.utc)

        return value.isoformat()

    @staticmethod
    def _datetime_from_storage(value: Any) -> datetime:
        """
        Wandelt einen Storage-Wert defensiv in ein timezone-aware UTC-datetime um.
        """
        if not value:
            return datetime.now(timezone.utc)

        if isinstance(value, datetime):
            if value.tzinfo is None:
                return value.replace(tzinfo=timezone.utc)
            return value.astimezone(timezone.utc)

        parsed = datetime.fromisoformat(str(value))
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)

        return parsed.astimezone(timezone.utc)