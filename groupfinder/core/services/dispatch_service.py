from __future__ import annotations

from ..models.context import Context
from ..models.search import Search
from .logging_service import LoggingService


class DispatchService:
    """
    Zentrale Dispatch-Schicht für Folgeaktionen nach erfolgreichen Mutationen.

    Im MVP wird noch kein echter Discord-Refresh oder Notification-Handling
    durchgeführt. Stattdessen werden saubere Ereignisse geloggt, damit die
    nachgelagerten Systemgrenzen bereits klar definiert sind.
    """

    def __init__(self, logging_service: LoggingService) -> None:
        self._logging = logging_service

    def dispatch_created(self, *, context: Context, search: Search) -> None:
        """Dispatch für neu erstellte Suchen."""
        self._logging.event(
            "search_created",
            context_key=context.context_key,
            search_id=search.search_id,
            module_key=search.module_key,
            content_key=search.content_key,
        )

    def dispatch_updated(self, *, context: Context, search: Search) -> None:
        """Dispatch für aktualisierte Suchen."""
        self._logging.event(
            "search_updated",
            context_key=context.context_key,
            search_id=search.search_id,
            status=search.status,
            participants=search.participant_count(),
            waitlist=search.waitlist_count(),
        )

    def dispatch_deleted(self, *, context: Context, search: Search) -> None:
        """Dispatch für gelöschte Suchen."""
        self._logging.event(
            "search_deleted",
            context_key=context.context_key,
            search_id=search.search_id,
            module_key=search.module_key,
            content_key=search.content_key,
        )