from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Tuple


@dataclass(slots=True, frozen=True)
class Context:
    """
    Repräsentiert den aktiven Betriebs- und Zielkontext für Groupfinder.

    Der Context trennt LIVE und TEST über Daten, nicht über getrennte Codepfade.
    Alle nachgelagerten Core-Services arbeiten mit diesem Objekt, statt sich
    ihre Zielwerte selbst aus Config oder Discord-Objekten zusammenzusuchen.
    """

    context_key: str
    guild_id: int

    command_channel_ids: Tuple[int, ...] = field(default_factory=tuple)
    command_category_ids: Tuple[int, ...] = field(default_factory=tuple)

    dashboard_channel_id: int | None = None
    log_channel_id: int | None = None

    allowed_role_ids: Tuple[int, ...] = field(default_factory=tuple)
    storage_namespace: str = "default"

    def is_live(self) -> bool:
        """Gibt zurück, ob es sich um den LIVE-Kontext handelt."""
        return self.context_key.upper() == "LIVE"

    def is_test(self) -> bool:
        """Gibt zurück, ob es sich um den TEST-Kontext handelt."""
        return self.context_key.upper() == "TEST"

    def allows_command_channel(
        self,
        channel_id: int,
        category_id: int | None = None,
    ) -> bool:
        """
        Prüft, ob ein Channel oder dessen Parent-Kategorie für diesen Context erlaubt ist.
        """
        if channel_id in self.command_channel_ids:
            return True

        if category_id is not None and category_id in self.command_category_ids:
            return True

        return False

    def has_allowed_role(self, role_ids: Iterable[int]) -> bool:
        """
        Prüft, ob mindestens eine der übergebenen Rollen in diesem Context erlaubt ist.
        """
        if not self.allowed_role_ids:
            return True

        return any(role_id in self.allowed_role_ids for role_id in role_ids)