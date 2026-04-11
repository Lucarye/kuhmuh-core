from __future__ import annotations

from ..models.context import Context
from ..models.session import FlowSession
from ..repository.session_repository import SessionRepository


class SessionService:
    """
    Verwalter für Flow-Sessions.

    Der Service kapselt den Lebenszyklus temporärer Create-/Edit-Sessions
    oberhalb des SessionRepository.
    """

    def __init__(self, session_repository: SessionRepository) -> None:
        self._session_repository = session_repository

    def create_session(
        self,
        *,
        context: Context,
        user_id: int,
        guild_id: int,
        mode: str,
        module_key: str,
        current_step: str,
        payload: dict | None = None,
    ) -> FlowSession:
        """
        Erstellt und speichert eine neue Flow-Session.
        """
        session = FlowSession(
            user_id=user_id,
            guild_id=guild_id,
            mode=mode,
            module_key=module_key,
            current_step=current_step,
            payload=payload or {},
        )
        return self._session_repository.save(session, context)

    def get_session(self, *, context: Context, user_id: int) -> FlowSession | None:
        """
        Lädt die Session eines Nutzers, sofern vorhanden und nicht abgelaufen.
        """
        session = self._session_repository.get(user_id, context)
        if session is None:
            return None

        if session.is_expired():
            self._session_repository.delete(user_id, context)
            return None

        return session

    def update_session(
        self,
        *,
        context: Context,
        user_id: int,
        current_step: str | None = None,
        payload_updates: dict | None = None,
        extend_minutes: int | None = 15,
    ) -> FlowSession | None:
        """
        Aktualisiert eine bestehende Session und speichert sie erneut.
        """
        session = self.get_session(context=context, user_id=user_id)
        if session is None:
            return None

        if current_step is not None:
            session.set_step(current_step)

        if payload_updates:
            session.update_payload(**payload_updates)

        if extend_minutes is not None:
            session.extend(minutes=extend_minutes)

        return self._session_repository.save(session, context)

    def delete_session(self, *, context: Context, user_id: int) -> FlowSession | None:
        """
        Entfernt die Session eines Nutzers.
        """
        return self._session_repository.delete(user_id, context)

    def cleanup_expired_sessions(self, *, context: Context) -> list[FlowSession]:
        """
        Entfernt alle abgelaufenen Sessions eines Contexts.
        """
        return self._session_repository.cleanup_expired(context)