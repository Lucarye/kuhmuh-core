from __future__ import annotations

from typing import Any

from ..models.context import Context
from ..models.session import FlowSession


class SessionRepository:
    """
    Repository für Flow-Sessions.

    Sessions werden intern als serialisierte Daten gehalten, damit persistente
    Speicherung und Restart-Recovery später sauber darauf aufbauen können.
    """

    def __init__(self) -> None:
        self._storage: dict[str, dict[str, dict[str, Any]]] = {}

    @staticmethod
    def _session_key(user_id: int, guild_id: int) -> str:
        """
        Baut einen stabilen Schlüssel für eine Session.
        """
        return f"{user_id}:{guild_id}"

    def get(self, user_id: int, guild_id: int, context: Context) -> FlowSession | None:
        """
        Lädt eine Session anhand von User-ID, Guild-ID und Context.
        """
        namespace = self._get_namespace(context)
        bucket = self._storage.get(namespace, {})
        session_data = bucket.get(self._session_key(user_id, guild_id))
        if session_data is None:
            return None

        return FlowSession.from_dict(session_data)

    def save(self, session: FlowSession, context: Context) -> FlowSession:
        """
        Speichert oder überschreibt eine Session.
        """
        namespace = self._get_namespace(context)
        bucket = self._storage.setdefault(namespace, {})
        bucket[self._session_key(session.user_id, session.guild_id)] = session.to_dict()
        return session

    def delete(self, user_id: int, guild_id: int, context: Context) -> FlowSession | None:
        """
        Löscht eine Session und gibt sie zurück, falls vorhanden.
        """
        namespace = self._get_namespace(context)
        bucket = self._storage.get(namespace, {})
        session_data = bucket.pop(self._session_key(user_id, guild_id), None)
        if session_data is None:
            return None

        return FlowSession.from_dict(session_data)

    def list_by_context(self, context: Context) -> list[FlowSession]:
        """
        Gibt alle Sessions des angegebenen Contexts zurück.
        """
        namespace = self._get_namespace(context)
        bucket = self._storage.get(namespace, {})
        return [
            FlowSession.from_dict(session_data)
            for session_data in bucket.values()
        ]

    def clear_context(self, context: Context) -> None:
        """
        Entfernt alle Sessions eines Contexts.
        """
        namespace = self._get_namespace(context)
        self._storage.pop(namespace, None)

    def export_context_data(self, context: Context) -> dict[str, dict[str, Any]]:
        """
        Exportiert die serialisierten Session-Daten eines Contexts.
        """
        namespace = self._get_namespace(context)
        bucket = self._storage.get(namespace, {})
        return {
            session_key: dict(session_data)
            for session_key, session_data in bucket.items()
        }

    def import_context_data(
        self,
        context: Context,
        data: dict[str, dict[str, Any]],
    ) -> None:
        """
        Importiert serialisierte Session-Daten in einen Context-Bucket.
        """
        namespace = self._get_namespace(context)
        self._storage[namespace] = {
            str(session_key): dict(session_data)
            for session_key, session_data in data.items()
        }

    @staticmethod
    def _get_namespace(context: Context) -> str:
        """Leitet den internen Speicher-Namespace aus dem Context ab."""
        return context.storage_namespace