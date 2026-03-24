from __future__ import annotations

import logging
from typing import Any


class LoggingService:
    """
    Dünne Logging-Abstraktion für den Core.

    Für das MVP wird bewusst das Standard-Logging von Python genutzt.
    Spätere Erweiterungen können hier strukturierte Discord-Logs oder
    weitergehende Event-Ausleitungen ergänzen, ohne die Core-Aufrufer zu ändern.
    """

    def __init__(self, logger_name: str = "groupfinder") -> None:
        self._logger = logging.getLogger(logger_name)

    def debug(self, message: str, **extra: Any) -> None:
        """Schreibt einen Debug-Logeintrag."""
        self._logger.debug(self._format(message, extra))

    def info(self, message: str, **extra: Any) -> None:
        """Schreibt einen Info-Logeintrag."""
        self._logger.info(self._format(message, extra))

    def warning(self, message: str, **extra: Any) -> None:
        """Schreibt einen Warning-Logeintrag."""
        self._logger.warning(self._format(message, extra))

    def error(self, message: str, **extra: Any) -> None:
        """Schreibt einen Error-Logeintrag."""
        self._logger.error(self._format(message, extra))

    def exception(self, message: str, **extra: Any) -> None:
        """Schreibt einen Exception-Logeintrag inklusive Traceback."""
        self._logger.exception(self._format(message, extra))

    def event(self, event_name: str, **extra: Any) -> None:
        """
        Schreibt ein generisches Ereignis-Log.

        Diese Methode ist hilfreich für fachliche Systemereignisse wie:
        - search_created
        - search_joined
        - search_closed
        """
        payload = {"event": event_name, **extra}
        self._logger.info(self._format("groupfinder_event", payload))

    @staticmethod
    def _format(message: str, extra: dict[str, Any]) -> str:
        """
        Formatiert einen Logeintrag kompakt und lesbar.
        """
        if not extra:
            return message

        serialized = ", ".join(f"{key}={value!r}" for key, value in sorted(extra.items()))
        return f"{message} | {serialized}"