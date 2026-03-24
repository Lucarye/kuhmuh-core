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

    # =========================
    # READ
    # =========================

    def get_search(self, *, context: Context, search_id: str) -> Search | None:
        return self._search_repository.get(search_id, context)

    def list_searches(self, *, context: Context) -> list[Search]:
        return self._search_repository.list_by_context(context)

    # =========================
    # CREATE
    # =========================

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
        if slots_total < 1:
            return OperationResult.fail(
                user_message="Die Gruppengröße muss mindestens 1 sein.",
                error_code="invalid_slots_total",
            )

        search = Search(
            search_id=uuid.uuid4().hex[:12],
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

        return OperationResult.ok(
            changed=True,
            user_message="Die Gruppensuche wurde erstellt.",
            search=search,
        )

    # =========================
    # JOIN
    # =========================

    async def join_search(
        self,
        *,
        context: Context,
        search_id: str,
        user_id: int,
        display_name: str,
    ) -> OperationResult:
        if self._interaction_guard.should_block_and_mark("join", user_id, search_id):
            return OperationResult.fail(
                user_message="Aktion bereits ausgelöst.",
                error_code="duplicate",
            )

        lock = await self._lock_service.get_lock(search_id)

        async with lock:
            search = self._search_repository.get(search_id, context)
            if not search:
                return OperationResult.fail(user_message="Suche nicht gefunden.")

            if not search.is_open():
                return OperationResult.fail(user_message="Suche ist geschlossen.")

            if search.has_participant(user_id):
                return OperationResult.fail(user_message="Bereits in der Gruppe.")

            if search.has_waitlist_user(user_id):
                return OperationResult.fail(user_message="Bereits auf Warteliste.")

            participant = Participant(user_id=user_id, display_name=display_name)

            if search.is_full():
                search.add_to_waitlist(participant)
                message = "Gruppe voll → Warteliste."
            else:
                search.add_participant(participant)
                message = "Du bist beigetreten."

            self._search_repository.save(search, context)

            return OperationResult.ok(
                changed=True,
                user_message=message,
                search=search,
            )

    # =========================
    # LEAVE
    # =========================

    async def leave_search(
        self,
        *,
        context: Context,
        search_id: str,
        user_id: int,
    ) -> OperationResult:
        if self._interaction_guard.should_block_and_mark("leave", user_id, search_id):
            return OperationResult.fail(user_message="Aktion bereits ausgelöst.")

        lock = await self._lock_service.get_lock(search_id)

        async with lock:
            search = self._search_repository.get(search_id, context)
            if not search:
                return OperationResult.fail(user_message="Suche nicht gefunden.")

            removed = search.remove_participant(user_id)
            if not removed:
                removed = search.remove_waitlist_user(user_id)

            if not removed:
                return OperationResult.fail(user_message="Du bist nicht Teil der Suche.")

            promoted = None
            if search.waitlist:
                promoted = search.pop_next_waitlist_user()
                if promoted:
                    search.add_participant(promoted)

            self._search_repository.save(search, context)

            return OperationResult.ok(
                changed=True,
                user_message="Du hast die Gruppe verlassen.",
                search=search,
            )

    # =========================
    # CLOSE
    # =========================

    async def close_search(
        self,
        *,
        context: Context,
        search_id: str,
        actor_user_id: int,
        actor_role_ids: tuple[int, ...] = (),
    ) -> OperationResult:
        lock = await self._lock_service.get_lock(search_id)

        async with lock:
            search = self._search_repository.get(search_id, context)
            if not search:
                return OperationResult.fail(user_message="Suche nicht gefunden.")

            if not self._can_manage_search(
                context=context,
                search=search,
                actor_user_id=actor_user_id,
                actor_role_ids=actor_role_ids,
            ):
                return OperationResult.fail(
                    user_message="Nur der Ersteller oder berechtigte Rollen dürfen diese Suche schließen.",
                    error_code="not_search_manager",
                    search=search,
                )

            if search.is_closed():
                return OperationResult.fail(user_message="Bereits geschlossen.")

            search.close()
            self._search_repository.save(search, context)

            return OperationResult.ok(
                changed=True,
                user_message="Suche geschlossen.",
                search=search,
            )

    # =========================
    # OPEN
    # =========================

    async def open_search(
        self,
        *,
        context: Context,
        search_id: str,
        actor_user_id: int,
        actor_role_ids: tuple[int, ...] = (),
    ) -> OperationResult:
        lock = await self._lock_service.get_lock(search_id)

        async with lock:
            search = self._search_repository.get(search_id, context)
            if not search:
                return OperationResult.fail(user_message="Suche nicht gefunden.")

            if not self._can_manage_search(
                context=context,
                search=search,
                actor_user_id=actor_user_id,
                actor_role_ids=actor_role_ids,
            ):
                return OperationResult.fail(
                    user_message="Nur der Ersteller oder berechtigte Rollen dürfen diese Suche öffnen.",
                    error_code="not_search_manager",
                    search=search,
                )

            if search.is_open():
                return OperationResult.fail(user_message="Bereits offen.")

            search.open()
            self._search_repository.save(search, context)

            return OperationResult.ok(
                changed=True,
                user_message="Suche geöffnet.",
                search=search,
            )

    # =========================
    # DELETE
    # =========================

    async def delete_search(
        self,
        *,
        context: Context,
        search_id: str,
        actor_user_id: int,
        actor_role_ids: tuple[int, ...] = (),
    ) -> OperationResult:
        lock = await self._lock_service.get_lock(search_id)

        async with lock:
            search = self._search_repository.get(search_id, context)
            if not search:
                return OperationResult.fail(user_message="Suche nicht gefunden.")

            if not self._can_manage_search(
                context=context,
                search=search,
                actor_user_id=actor_user_id,
                actor_role_ids=actor_role_ids,
            ):
                return OperationResult.fail(
                    user_message="Nur der Ersteller oder berechtigte Rollen dürfen diese Suche löschen.",
                    error_code="not_search_manager",
                    search=search,
                )

            self._search_repository.delete(search_id, context)

            return OperationResult.ok(
                changed=True,
                user_message="Suche wurde gelöscht.",
                search=None,
            )

    def _can_manage_search(
        self,
        *,
        context: Context,
        search: Search,
        actor_user_id: int,
        actor_role_ids: tuple[int, ...] = (),
    ) -> bool:
        """
        Prüft, ob ein Nutzer eine Suche verwalten darf.

        Erlaubt sind:
        - der Ersteller der Suche
        - Nutzer mit einer Rolle, die im aktuellen Context freigegeben ist
        """
        if search.creator_id == actor_user_id:
            return True

        if not context.allowed_role_ids:
            return False

        return any(role_id in context.allowed_role_ids for role_id in actor_role_ids)