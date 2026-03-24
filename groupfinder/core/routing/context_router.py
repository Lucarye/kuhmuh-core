from __future__ import annotations

from ..models.context import Context


class ContextRouter:
    """
    Löst den aktiven Groupfinder-Context aus Laufzeitdaten auf.

    Für das MVP arbeitet der Router bewusst mit einfachen primitiven Eingaben
    wie Guild-ID, Channel-ID, Parent-Kategorie und Rollenlisten.
    Discord-spezifische Objekte sollen nicht in das Kernmodell hineinreichen.
    """

    def __init__(self, contexts: list[Context]) -> None:
        self._contexts = contexts

    def resolve(
        self,
        *,
        guild_id: int,
        channel_id: int,
        category_id: int | None,
        role_ids: list[int] | tuple[int, ...] | set[int],
    ) -> Context | None:
        """
        Ermittelt den ersten passenden Context.

        Ein Context gilt als passend, wenn:
        - Guild-ID übereinstimmt
        - Channel oder Parent-Kategorie erlaubt ist
        - mindestens eine Rolle erlaubt ist
        """
        for context in self._contexts:
            if context.guild_id != guild_id:
                continue

            if not context.allows_command_channel(
                channel_id=channel_id,
                category_id=category_id,
            ):
                continue

            if not context.has_allowed_role(role_ids):
                continue

            return context

        return None

    def resolve_by_key(self, context_key: str) -> Context | None:
        """
        Ermittelt einen Context direkt über seinen Schlüssel.
        """
        for context in self._contexts:
            if context.context_key.upper() == context_key.upper():
                return context
        return None

    def all_contexts(self) -> list[Context]:
        """
        Gibt alle bekannten Contexts zurück.
        """
        return list(self._contexts)