from __future__ import annotations

import uuid

from ..models.context import Context
from ..models.operation_result import OperationResult
from ..models.participant import Participant
from ..models.search import Search
from ..repository.search_repository import SearchRepository
from .dispatch_service import DispatchService
from .interaction_guard_service import InteractionGuardService
from .lock_service import LockService
from .logging_service import LoggingService


class SearchService:
    """
    Kernservice für den generischen Search-Lifecycle.

    Der Service kapselt alle mutierenden und lesenden Kernoperationen auf Search-
    Objekten. Fachliche Modulregeln oder UI-Darstellung gehören nicht hier hinein.
    """

    def __init__(
        self,
        *,
        search_repository: SearchRepository,
        lock_service: LockService,
        interaction_guard_service: InteractionGuardService,
        logging_service: LoggingService,
        dispatch_service: DispatchService,
    ) -> None:
        self._search_repository = search_repository
        self._lock_service = lock_service
        self._interaction_guard = interaction_guard_service
        self._logging = logging_service
        self._dispatch = dispatch_service

    def get_search(self, *, context: Context, search_id: str) -> Search | None:
        """
        Lädt eine Suche anhand ihrer ID.
        """
        return self._search_repository.get(search_id, context)

    def list_searches(self, *, context: Context) -> list[Search]:
        """
        Gibt alle Suchen des Contexts zurück.
        """
        return self._search_repository.list_by_context(context)

    def create_search(
        self,
        *,
        context: Context,
        module_key: str,
        content_key: str,
        guild_id: int,
        channel_id: int,
        creator_id: int,
        slots_total: int,
        payload: dict | None = None,
    ) -> OperationResult:
        """
        Erstellt und speichert eine neue Suche.

        Der Ersteller wird im MVP nicht automatisch als Teilnehmer eingetragen.
        Diese Entscheidung bleibt bewusst explizit, damit sie später pro Modul
        oder Flow sauber gesteuert werden kann.
        """
        if slots_total < 1:
            return OperationResult.fail(
                user_message="Die Gruppengröße muss mindestens 1 sein.",
                error_code="invalid_slots_total",
            )

        search = Search(
            search_id=self._generate_search_id(),
            module_key=module_key,
            content_key=content_key,
            context_key=context.context_key,
            guild_id=guild_id,
            channel_id=channel_id,
            creator_id=creator_id,
            slots_total=slots_total,
            payload=payload or {},
        )

        self._search_repository.save(search, context)
        self._dispatch.dispatch_created(context=context, search=search)
        self._logging.event(
            "search_created_core",
            context_key=context.context_key,
            search_id=search.search_id,
            creator_id=creator_id,
        )

        return OperationResult.ok(
            changed=True,
            user_message="Die Gruppensuche wurde erstellt.",
            dispatch_required=True,
            search=search,
        )

    async def join_search(
        self,
        *,
        context: Context,
        search_id: str,
        user_id: int,
        display_name: str,
    ) -> OperationResult:
        """
        Fügt einen Nutzer einer Suche hinzu.

        Ist die Suche voll, wird der Nutzer auf die Warteliste gesetzt.
        """
        if self._interaction_guard.should_block_and_mark("join", user_id, search_id):
            return OperationResult.fail(
                user_message="Die Aktion wurde gerade bereits ausgelöst.",
                error_code="duplicate_interaction",
            )

        lock = await self._lock_service.get_lock(search_id)

        async with lock:
            search = self._search_repository.get(search_id, context)
            if search is None:
                return OperationResult.fail(
                    user_message="Die Gruppensuche wurde nicht gefunden.",
                    error_code="search_not_found",
                )

            if search.has_participant(user_id):
                return OperationResult.fail(
                    user_message="Du bist bereits in der Gruppe.",
                    error_code="already_joined",
                    search=search,
                )

            if search.has_waitlist_user(user_id):
                return OperationResult.fail(
                    user_message="Du stehst bereits auf der Warteliste.",
                    error_code="already_waitlisted",
                    search=search,
                )

            if not search.is_open():
                return OperationResult.fail(
                    user_message="Diese Gruppensuche ist geschlossen.",
                    error_code="search_closed",
                    search=search,
                )

            participant = Participant(
                user_id=user_id,
                display_name=display_name,
            )

            if search.is_full():
                search.add_to_waitlist(participant)
                result_message = "Die Gruppe ist voll. Du wurdest auf die Warteliste gesetzt."
            else:
                search.add_participant(participant)
                result_message = "Du bist der Gruppe beigetreten."

            self._search_repository.save(search, context)
            self._dispatch.dispatch_updated(context=context, search=search)
            self._logging.event(
                "search_joined",
                search_id=search.search_id,
                user_id=user_id,
                waitlisted=search.has_waitlist_user(user_id),
            )

            return OperationResult.ok(
                changed=True,
                user_message=result_message,
                dispatch_required=True,
                search=search,
            )

    async def leave_search(
        self,
        *,
        context: Context,
        search_id: str,
        user_id: int,
    ) -> OperationResult:
        """
        Entfernt einen Nutzer aus Gruppe oder Warteliste.

        Falls ein regulärer Platz frei wird, rückt der nächste Wartelisten-Eintrag nach.
        """
        if self._interaction_guard.should_block_and_mark("leave", user_id, search_id):
            return OperationResult.fail(
                user_message="Die Aktion wurde gerade bereits ausgelöst.",
                error_code="duplicate_interaction",
            )

        lock = await self._lock_service.get_lock(search_id)

        async with lock:
            search = self._search_repository.get(search_id, context)
            if search is None:
                return OperationResult.fail(
                    user_message="Die Gruppensuche wurde nicht gefunden.",
                    error_code="search_not_found",
                )

            removed_participant = search.remove_participant(user_id)
            removed_waitlist_user = None

            if removed_participant is None:
                removed_waitlist_user = search.remove_waitlist_user(user_id)

            if removed_participant is None and removed_waitlist_user is None:
                return OperationResult.fail(
                    user_message="Du bist nicht Teil dieser Gruppensuche.",
                    error_code="not_in_search",
                    search=search,
                )

            promoted_user = None
            if removed_participant is not None and search.waitlist_count() > 0:
                promoted_user = search.pop_next_waitlist_user()
                if promoted_user is not None:
                    search.add_participant(promoted_user)

            self._search_repository.save(search, context)
            self._dispatch.dispatch_updated(context=context, search=search)
            self._logging.event(
                "search_left",
                search_id=search.search_id,
                user_id=user_id,
                promoted_user_id=promoted_user.user_id if promoted_user else None,
            )

            if removed_waitlist_user is not None:
                message = "Du wurdest von der Warteliste entfernt."
            else:
                message = "Du hast die Gruppe verlassen."

            return OperationResult.ok(
                changed=True,
                user_message=message,
                dispatch_required=True,
                search=search,
                extra={
                    "promoted_user_id": promoted_user.user_id if promoted_user else None,
                },
            )

    async def close_search(
        self,
        *,
        context: Context,
        search_id: str,
        actor_user_id: int,
    ) -> OperationResult:
        """
        Schließt eine Suche.
        """
        if self._interaction_guard.should_block_and_mark("close", actor_user_id, search_id):
            return OperationResult.fail(
                user_message="Die Aktion wurde gerade bereits ausgelöst.",
                error_code="duplicate_interaction",
            )

        lock = await self._lock_service.get_lock(search_id)

        async with lock:
            search = self._search_repository.get(search_id, context)
            if search is None:
                return OperationResult.fail(
                    user_message="Die Gruppensuche wurde nicht gefunden.",
                    error_code="search_not_found",
                )

            if search.is_closed():
                return OperationResult.fail(
                    user_message="Die Gruppensuche ist bereits geschlossen.",
                    error_code="already_closed",
                    search=search,
                )

            search.close()
            self._search_repository.save(search, context)
            self._dispatch.dispatch_updated(context=context, search=search)
            self._logging.event(
                "search_closed",
                search_id=search.search_id,
                actor_user_id=actor_user_id,
            )

            return OperationResult.ok(
                changed=True,
                user_message="Die Gruppensuche wurde geschlossen.",
                dispatch_required=True,
                search=search,
            )

    async def open_search(
        self,
        *,
        context: Context,
        search_id: str,
        actor_user_id: int,
    ) -> OperationResult:
        """
        Öffnet eine zuvor geschlossene Suche erneut.
        """
        if self._interaction_guard.should_block_and_mark("open", actor_user_id, search_id):
            return OperationResult.fail(
                user_message="Die Aktion wurde gerade bereits ausgelöst.",
                error_code="duplicate_interaction",
            )

        lock = await self._lock_service.get_lock(search_id)

        async with lock:
            search = self._search_repository.get(search_id, context)
            if search is None:
                return OperationResult.fail(
                    user_message="Die Gruppensuche wurde nicht gefunden.",
                    error_code="search_not_found",
                )

            if search.is_open():
                return OperationResult.fail(
                    user_message="Die Gruppensuche ist bereits offen.",
                    error_code="already_open",
                    search=search,
                )

            search.open()
            self._search_repository.save(search, context)
            self._dispatch.dispatch_updated(context=context, search=search)
            self._logging.event(
                "search_opened",
                search_id=search.search_id,
                actor_user_id=actor_user_id,
            )

            return OperationResult.ok(
                changed=True,
                user_message="Die Gruppensuche wurde wieder geöffnet.",
                dispatch_required=True,
                search=search,
            )

    async def delete_search(
        self,
        *,
        context: Context,
        search_id: str,
        actor_user_id: int,
    ) -> OperationResult:
        """
        Löscht eine Suche endgültig aus dem Repository.
        """
        if self._interaction_guard.should_block_and_mark("delete", actor_user_id, search_id):
            return OperationResult.fail(
                user_message="Die Aktion wurde gerade bereits ausgelöst.",
                error_code="duplicate_interaction",
            )

        lock = await self._lock_service.get_lock(search_id)

        async with lock:
            search = self._search_repository.get(search_id, context)
            if search is None:
                return OperationResult.fail(
                    user_message="Die Gruppensuche wurde nicht gefunden.",
                    error_code="search_not_found",
                )

            removed = self._search_repository.delete(search_id, context)
            if removed is None:
                return OperationResult.fail(
                    user_message="Die Gruppensuche konnte nicht gelöscht werden.",
                    error_code="delete_failed",
                    search=search,
                )

            self._dispatch.dispatch_deleted(context=context, search=removed)
            self._logging.event(
                "search_deleted_core",
                search_id=search_id,
                actor_user_id=actor_user_id,
            )

            return OperationResult.ok(
                changed=True,
                user_message="Die Gruppensuche wurde gelöscht.",
                dispatch_required=True,
                search=removed,
            )

    @staticmethod
    def _generate_search_id() -> str:
        """
        Erzeugt eine kurze, stabile ID für neue Gruppensuchen.
        """
        return uuid.uuid4().hex[:12]