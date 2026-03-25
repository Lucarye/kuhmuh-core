from __future__ import annotations

from typing import Any

from ..models.context import Context
from ..models.search import Search


class SearchRepository:
    """
    Repository für Groupfinder-Suchen.

    Die interne Storage-Struktur hält serialisierte Daten und nicht die
    Modellobjekte selbst. Dadurch wird der Übergang zu echter Persistenz
    wesentlich einfacher und sauberer.
    """

    def __init__(self) -> None:
        self._storage: dict[str, dict[str, dict[str, Any]]] = {}

    def list_by_context(self, context: Context) -> list[Search]:
        """
        Gibt alle Searches für den angegebenen Context zurück.
        """
        namespace = self._get_namespace(context)
        bucket = self._storage.get(namespace, {})
        return [
            Search.from_dict(search_data)
            for search_data in bucket.values()
        ]

    def get(self, search_id: str, context: Context) -> Search | None:
        """
        Lädt eine Search über Search-ID und Context.
        """
        namespace = self._get_namespace(context)
        bucket = self._storage.get(namespace, {})
        search_data = bucket.get(search_id)
        if search_data is None:
            return None

        return Search.from_dict(search_data)

    def save(self, search: Search, context: Context) -> Search:
        """
        Speichert oder überschreibt eine Search im Context-Bucket.
        """
        namespace = self._get_namespace(context)
        bucket = self._storage.setdefault(namespace, {})
        bucket[search.search_id] = search.to_dict()
        return search

    def delete(self, search_id: str, context: Context) -> Search | None:
        """
        Löscht eine Search aus dem Context-Bucket und gibt sie zurück, falls vorhanden.
        """
        namespace = self._get_namespace(context)
        bucket = self._storage.get(namespace, {})
        search_data = bucket.pop(search_id, None)
        if search_data is None:
            return None

        return Search.from_dict(search_data)

    def clear_context(self, context: Context) -> None:
        """
        Entfernt alle Searches eines Contexts.
        """
        namespace = self._get_namespace(context)
        self._storage.pop(namespace, None)

    def export_context_data(self, context: Context) -> dict[str, dict[str, Any]]:
        """
        Exportiert die serialisierten Search-Daten eines Contexts.
        """
        namespace = self._get_namespace(context)
        bucket = self._storage.get(namespace, {})
        return {
            search_id: dict(search_data)
            for search_id, search_data in bucket.items()
        }

    def import_context_data(
        self,
        context: Context,
        data: dict[str, dict[str, Any]],
    ) -> None:
        """
        Importiert serialisierte Search-Daten in einen Context-Bucket.
        """
        namespace = self._get_namespace(context)
        self._storage[namespace] = {
            str(search_id): dict(search_data)
            for search_id, search_data in data.items()
        }
        
    @staticmethod
    def _get_namespace(context: Context) -> str:
        """Leitet den internen Speicher-Namespace aus dem Context ab."""
        return f"v2:{context.storage_namespace}"