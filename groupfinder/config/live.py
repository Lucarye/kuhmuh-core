from __future__ import annotations

from ..core.models.context import Context
from .shared import LIVE_CONTEXT_KEY, LIVE_STORAGE_NAMESPACE


LIVE_CONTEXT = Context(
    context_key=LIVE_CONTEXT_KEY,

    # Kuhmuh Discord
    guild_id=1198649628787212458,

    command_channel_ids=(
        # LIVE: Gruppensuche V2
        1486128654332203140,
    ),
    command_category_ids=(),

    # Noch nicht gesetzt
    dashboard_channel_id=0,
    log_channel_id=0,

    # LIVE aktuell ohne Rollenbeschränkung
    allowed_role_ids=(),

    storage_namespace=LIVE_STORAGE_NAMESPACE,
)