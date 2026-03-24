from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from .participant import Participant


@dataclass(slots=True)
class Search:
    """
    Zentrales Domänenobjekt einer Gruppensuche.

    Search enthält ausschließlich generische Kerndaten. Fachliche oder
    spielbezogene Details werden über `payload` ergänzt, damit der Core
    selbst nicht content- oder game-spezifisch wird.
    """

    search_id: str
    module_key: str
    content_key: str
    context_key: str

    guild_id: int
    channel_id: int
    creator_id: int

    status: str = "OPEN"
    slots_total: int = 0

    participants: list[Participant] = field(default_factory=list)
    waitlist: list[Participant] = field(default_factory=list)

    payload: dict[str, Any] = field(default_factory=dict)

    public_message_id: int | None = None
    dashboard_message_id: int | None = None

    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def is_open(self) -> bool:
        """Gibt zurück, ob die Suche aktuell offen ist."""
        return self.status.upper() == "OPEN"

    def is_closed(self) -> bool:
        """Gibt zurück, ob die Suche aktuell geschlossen ist."""
        return self.status.upper() == "CLOSED"

    def is_full(self) -> bool:
        """Gibt zurück, ob alle regulären Plätze belegt sind."""
        return len(self.participants) >= self.slots_total

    def participant_count(self) -> int:
        """Gibt die Anzahl regulärer Teilnehmer zurück."""
        return len(self.participants)

    def waitlist_count(self) -> int:
        """Gibt die Anzahl der Wartelisten-Einträge zurück."""
        return len(self.waitlist)

    def has_participant(self, user_id: int) -> bool:
        """Prüft, ob ein Nutzer bereits regulärer Teilnehmer ist."""
        return any(participant.user_id == user_id for participant in self.participants)

    def has_waitlist_user(self, user_id: int) -> bool:
        """Prüft, ob ein Nutzer bereits auf der Warteliste steht."""
        return any(participant.user_id == user_id for participant in self.waitlist)

    def find_participant(self, user_id: int) -> Participant | None:
        """Liefert den regulären Teilnehmer mit passender User-ID, falls vorhanden."""
        for participant in self.participants:
            if participant.user_id == user_id:
                return participant
        return None

    def find_waitlist_user(self, user_id: int) -> Participant | None:
        """Liefert den Wartelisten-Eintrag mit passender User-ID, falls vorhanden."""
        for participant in self.waitlist:
            if participant.user_id == user_id:
                return participant
        return None

    def add_participant(self, participant: Participant) -> None:
        """
        Fügt einen Teilnehmer zur regulären Teilnehmerliste hinzu.

        Diese Methode führt bewusst keine komplexe Validierung durch.
        Geschäftsregeln wie Statusprüfung, Slotprüfung oder Duplicate-Schutz
        gehören in den SearchService.
        """
        self.participants.append(participant)
        self.touch()

    def add_to_waitlist(self, participant: Participant) -> None:
        """
        Fügt einen Teilnehmer zur Warteliste hinzu.

        Fachliche Regeln bleiben außerhalb des Modells.
        """
        self.waitlist.append(participant)
        self.touch()

    def remove_participant(self, user_id: int) -> Participant | None:
        """Entfernt einen regulären Teilnehmer anhand der User-ID."""
        for index, participant in enumerate(self.participants):
            if participant.user_id == user_id:
                removed = self.participants.pop(index)
                self.touch()
                return removed
        return None

    def remove_waitlist_user(self, user_id: int) -> Participant | None:
        """Entfernt einen Wartelisten-Eintrag anhand der User-ID."""
        for index, participant in enumerate(self.waitlist):
            if participant.user_id == user_id:
                removed = self.waitlist.pop(index)
                self.touch()
                return removed
        return None

    def pop_next_waitlist_user(self) -> Participant | None:
        """Zieht den nächsten Nutzer aus der Warteliste, falls vorhanden."""
        if not self.waitlist:
            return None

        participant = self.waitlist.pop(0)
        self.touch()
        return participant

    def open(self) -> None:
        """Setzt den Status der Suche auf OPEN."""
        self.status = "OPEN"
        self.touch()

    def close(self) -> None:
        """Setzt den Status der Suche auf CLOSED."""
        self.status = "CLOSED"
        self.touch()

    def touch(self) -> None:
        """Aktualisiert den Änderungszeitpunkt der Suche."""
        self.updated_at = datetime.now(timezone.utc)