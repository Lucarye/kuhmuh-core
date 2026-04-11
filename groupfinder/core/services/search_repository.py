from __future__ import annotations

from typing import Dict

from ..models.context import Context
from ..models.search import Search


class SearchRepository:
    """
    In-Memory-Repository für Search-Objekte.

    Das Repository kapselt den Speicherzugriff vollständig vom restlichen Core.
    Für das MVP wird bewusst ein einfacher In-Memory-Speicher genutzt.
    Spätere Persistenzvarianten sollen dieselbe öffentliche Schnittstelle bedienen.
    """

    def __init__(self) -> None:
        self._storage: dict[str, Dict[str, Search]] = {}

    def get(self, search_id: str, context: Context) -> Search | None:
        """Lädt eine Suche anhand ihrer ID im gegebenen Context."""
        namespace = self._get_namespace(context)
        return self._storage.get(namespace, {}).get(search_id)

    def save(self, search: Search, context: Context) -> Search:
        """Speichert oder überschreibt eine Suche im gegebenen Context."""
        namespace = self._get_namespace(context)
        bucket = self._storage.setdefault(namespace, {})
        bucket[search.search_id] = search
        return search

    def delete(self, search_id: str, context: Context) -> Search | None:
        """Entfernt eine Suche anhand ihrer ID aus dem gegebenen Context."""
        namespace = self._get_namespace(context)
        bucket = self._storage.get(namespace, {})
        return bucket.pop(search_id, None)

    def list_by_context(self, context: Context) -> list[Search]:
        """Gibt alle Suchen innerhalb des gegebenen Contexts zurück."""
        namespace = self._get_namespace(context)
        bucket = self._storage.get(namespace, {})
        return list(bucket.values())

    def exists(self, search_id: str, context: Context) -> bool:
        """Prüft, ob eine Suche im gegebenen Context existiert."""
        return self.get(search_id, context) is not None

    def clear_context(self, context: Context) -> None:
        """Entfernt alle Suchen des gegebenen Contexts."""
        namespace = self._get_namespace(context)
        self._storage.pop(namespace, None)

    @staticmethod
    def _get_namespace(context: Context) -> str:
        """Leitet den internen Speicher-Namespace aus dem Context ab."""
        return context.storage_namespace