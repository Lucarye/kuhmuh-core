from __future__ import annotations

from ..core.models.context import Context
from .shared import TEST_CONTEXT_KEY, TEST_STORAGE_NAMESPACE


TEST_CONTEXT = Context(
    context_key=TEST_CONTEXT_KEY,

    # Kuhmuh Discord
    guild_id=1198649628787212458,

    # TEST läuft über die Bot-Test-Kategorie
    command_channel_ids=(),
    command_category_ids=(
        # TEST: Bot-Test-Ecke
        1460005712041349201,
    ),

    # Noch nicht gesetzt
    dashboard_channel_id=0,
    log_channel_id=0,

    allowed_role_ids=(
        # TEST: dedizierte Testrolle
        1445018518562017373,

        # Leitung / Team
        1452050940952838214,  # Admin
        1198652039312453723,  # Offizier
    ),

    storage_namespace=TEST_STORAGE_NAMESPACE,
)