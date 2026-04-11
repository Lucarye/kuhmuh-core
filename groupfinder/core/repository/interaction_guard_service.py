from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone


@dataclass(slots=True, frozen=True)
class _GuardKey:
    """Eindeutiger Schlüssel für eine geschützte Aktion."""
    action: str
    user_id: int
    target_id: str


class InteractionGuardService:
    """
    Schützt gegen mehrfach ausgelöste identische Interaktionen in kurzer Zeit.

    Typische Fälle:
    - Doppelklick auf Join
    - mehrfaches Close/Delete
    - parallele Button-Auslösung durch denselben Nutzer
    """

    def __init__(self, window_seconds: int = 3) -> None:
        self._window = timedelta(seconds=window_seconds)
        self._entries: dict[_GuardKey, datetime] = {}

    def should_block(self, action: str, user_id: int, target_id: str) -> bool:
        """
        Prüft, ob die angefragte Aktion aktuell noch innerhalb des Sperrfensters liegt.
        """
        self.cleanup()

        key = _GuardKey(action=action, user_id=user_id, target_id=target_id)
        last_seen = self._entries.get(key)

        if last_seen is None:
            return False

        return datetime.now(timezone.utc) - last_seen < self._window

    def mark(self, action: str, user_id: int, target_id: str) -> None:
        """
        Markiert eine Aktion als gerade ausgeführt.
        """
        key = _GuardKey(action=action, user_id=user_id, target_id=target_id)
        self._entries[key] = datetime.now(timezone.utc)

    def should_block_and_mark(self, action: str, user_id: int, target_id: str) -> bool:
        """
        Kombinierte Komfortmethode:
        - gibt True zurück, wenn geblockt werden soll
        - markiert andernfalls die Aktion direkt
        """
        if self.should_block(action, user_id, target_id):
            return True

        self.mark(action, user_id, target_id)
        return False

    def cleanup(self) -> int:
        """
        Entfernt veraltete Guard-Einträge und gibt die Anzahl der entfernten Einträge zurück.
        """
        now = datetime.now(timezone.utc)

        expired_keys = [
            key
            for key, timestamp in self._entries.items()
            if now - timestamp >= self._window
        ]

        for key in expired_keys:
            self._entries.pop(key, None)

        return len(expired_keys)