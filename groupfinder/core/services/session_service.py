from __future__ import annotations

from ..models.context import Context
from ..models.session import FlowSession
from ..repository.session_repository import SessionRepository


class SessionService:
    """
    Verwalter für Flow-Sessions.
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
        session = FlowSession(
            user_id=user_id,
            guild_id=guild_id,
            mode=mode,
            module_key=module_key,
            current_step=current_step,
            payload=payload or {},
        )
        return self._session_repository.save(session, context)