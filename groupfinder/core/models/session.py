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