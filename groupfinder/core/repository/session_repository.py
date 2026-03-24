from __future__ import annotations

from typing import Dict

from ..models.context import Context
from ..models.session import FlowSession


class SessionRepository:
    """
    In-Memory-Repository für Flow-Sessions.

    Sessions sind temporäre Zustandsobjekte für UI- und Erstell-/Edit-Flows.
    Das Repository trennt auch diesen Speicherzugriff sauber vom restlichen Core.
    """

    def __init__(self) -> None:
        self._storage: dict[str, Dict[int, FlowSession]] = {}

    def get(self, user_id: int, context: Context) -> FlowSession | None:
        """Lädt die Session eines Users im gegebenen Context."""
        namespace = self._get_namespace(context)
        return self._storage.get(namespace, {}).get(user_id)

    def save(self, session: FlowSession, context: Context) -> FlowSession:
        """Speichert oder überschreibt eine Session im gegebenen Context."""
        namespace = self._get_namespace(context)
        bucket = self._storage.setdefault(namespace, {})
        bucket[session.user_id] = session
        return session

    def delete(self, user_id: int, context: Context) -> FlowSession | None:
        """Entfernt die Session eines Users im gegebenen Context."""
        namespace = self._get_namespace(context)
        bucket = self._storage.get(namespace, {})
        return bucket.pop(user_id, None)

    def cleanup_expired(self, context: Context) -> list[FlowSession]:
        """
        Entfernt alle abgelaufenen Sessions im gegebenen Context
        und gibt die entfernten Sessions zurück.
        """
        namespace = self._get_namespace(context)
        bucket = self._storage.get(namespace, {})

        expired_user_ids = [
            user_id for user_id, session in bucket.items() if session.is_expired()
        ]

        removed_sessions: list[FlowSession] = []
        for user_id in expired_user_ids:
            removed = bucket.pop(user_id, None)
            if removed is not None:
                removed_sessions.append(removed)

        return removed_sessions

    def clear_context(self, context: Context) -> None:
        """Entfernt alle Sessions des gegebenen Contexts."""
        namespace = self._get_namespace(context)
        self._storage.pop(namespace, None)

    @staticmethod
    def _get_namespace(context: Context) -> str:
        """Leitet den internen Speicher-Namespace aus dem Context ab."""
        return context.storage_namespace