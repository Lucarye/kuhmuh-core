from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass(slots=True)
class _TrackedLock:
    """
    Interne Struktur für einen nachverfolgten Lock.

    Der Lock selbst ist technisch, die Zeitstempel dienen nur zur späteren Bereinigung.
    """

    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    last_used_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class LockService:
    """
    Verwaltet Locks pro Search-ID.

    Ziel ist es, mutierende Aktionen wie Join, Leave, Open, Close oder Delete
    pro Suche seriell auszuführen, um Race Conditions zu verhindern.
    """

    def __init__(self) -> None:
        self._locks: dict[str, _TrackedLock] = {}
        self._registry_lock = asyncio.Lock()

    async def get_lock(self, search_id: str) -> asyncio.Lock:
        """
        Gibt den Lock für eine Search-ID zurück und legt ihn bei Bedarf an.
        """
        async with self._registry_lock:
            tracked = self._locks.get(search_id)
            if tracked is None:
                tracked = _TrackedLock()
                self._locks[search_id] = tracked

            tracked.last_used_at = datetime.now(timezone.utc)
            return tracked.lock

    async def cleanup_unused(self) -> int:
        """
        Entfernt aktuell ungenutzte, nicht gesperrte Locks aus der Registry.

        Gibt die Anzahl der entfernten Locks zurück.
        """
        async with self._registry_lock:
            removable_keys = [
                key
                for key, tracked in self._locks.items()
                if not tracked.lock.locked()
            ]

            for key in removable_keys:
                self._locks.pop(key, None)

            return len(removable_keys)

    async def touch(self, search_id: str) -> None:
        """Aktualisiert den Nutzungszeitpunkt eines vorhandenen Locks."""
        async with self._registry_lock:
            tracked = self._locks.get(search_id)
            if tracked is not None:
                tracked.last_used_at = datetime.now(timezone.utc)