from __future__ import annotations

from ...core.models.search import Search
from ...modules.groupfinder.module import GroupFinderModule


class SearchRenderer:
    """
    Baut strukturierte Darstellungsdaten aus Search + Modul-Displaydaten.

    Diese Klasse kennt weiterhin keine Businesslogik des Core und führt
    keine Mutationen aus. Sie bereitet nur Daten für die UI-Aufbereitung vor.
    """

    def __init__(self, module: GroupFinderModule) -> None:
        self._module = module

    def render_search(self, search: Search) -> dict:
        """
        Liefert eine neutrale Darstellungsstruktur für eine Gruppensuche.
        """
        display_data = self._module.build_display_data(
            content_key=search.content_key,
            payload=search.payload,
        )

        participants = [
            participant.display_name for participant in search.participants
        ]
        waitlist = [
            participant.display_name for participant in search.waitlist
        ]

        return {
            "search_id": search.search_id,
            "title": display_data.get("title", "Gruppensuche"),
            "subtitle": display_data.get("subtitle", ""),
            "lines": display_data.get("lines", []),
            "status": search.status,
            "slots_total": search.slots_total,
            "participant_count": search.participant_count(),
            "waitlist_count": search.waitlist_count(),
            "participants": participants,
            "waitlist": waitlist,
            "creator_id": search.creator_id,
            "content_key": search.content_key,
            "module_key": search.module_key,
        }