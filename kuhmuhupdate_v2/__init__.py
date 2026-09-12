from redbot.core.bot import Red
from redbot.core.utils import get_end_user_data_statement_or_raise

from .kuhmuhupdate_v2 import KuhmuhUpdateV2

__red_end_user_data_statement__ = get_end_user_data_statement_or_raise(__file__)


async def setup(bot: Red) -> None:
    cog = KuhmuhUpdateV2(bot)
    await bot.add_cog(cog)

    admin_hub = bot.get_cog("AdminHubCog")
    if admin_hub is not None and cog.ADMIN_HUB_ENABLED:
        admin_hub.register_panel(cog.get_admin_panel())
