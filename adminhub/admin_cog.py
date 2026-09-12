from __future__ import annotations

import contextlib
import logging

import discord
from discord import app_commands
from redbot.core import Config, commands

from .registry import AdminPanelRegistry
from .views.main_menu import AdminHubView

GUILD_ID = 1198649628787212458
OWNER_ID = 359447597427064833
ADMIN_ROLE_ID = 1198650646786736240
OFFIZIER_ROLE_ID = 1198652039312453723

log = logging.getLogger("red.kuhmuh.adminhub")

DEFAULT_GUILD = {
    "panel_channel_id": None,
    "panel_message_id": None,
}

ACTION_CHOICES = [
    app_commands.Choice(name="Posten / Verschieben", value="post"),
    app_commands.Choice(name="Refresh", value="refresh"),
]


class AdminHubCog(commands.Cog):
    """
    Zentraler Einstiegspunkt fuer administrative Kuhmuh-Module (V2).

    Der Hub selbst enthaelt bewusst keine fachliche Logik. Er zeigt ein
    dauerhaftes Panel mit den registrierten Admin-Modulen und delegiert
    jede Aktion an das jeweils zustaendige, spaeter migrierte Modul.
    """

    def __init__(self, bot) -> None:
        self.bot = bot
        self.config = Config.get_conf(self, identifier=0x4B55484D41444D31, force_registration=True)
        self.config.register_guild(**DEFAULT_GUILD)
        self.registry = AdminPanelRegistry()
        self._startup_task = self.bot.loop.create_task(self._startup_guild_sync())

    async def _startup_guild_sync(self) -> None:
        await self.bot.wait_until_red_ready()
        await self.bot.wait_until_ready()
        with contextlib.suppress(Exception):
            self.bot.add_view(AdminHubView(self))
        with contextlib.suppress(Exception):
            await self.bot.tree.sync(guild=discord.Object(id=GUILD_ID))

    def cog_unload(self) -> None:
        if self._startup_task and not self._startup_task.done():
            self._startup_task.cancel()

    # -------------------------
    # Berechtigungen
    # -------------------------
    def is_authorized(self, user: discord.abc.User) -> bool:
        if user.id == OWNER_ID:
            return True
        role_ids = {role.id for role in getattr(user, "roles", ())}
        return bool(role_ids & {ADMIN_ROLE_ID, OFFIZIER_ROLE_ID})

    # -------------------------
    # Panel-Aufbau
    # -------------------------
    def build_main_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title="Kuhmuh Admin-Hub",
            description="Zentrale Steuerung fuer administrative Kuhmuh-Module.",
            color=discord.Color.blurple(),
        )

        panels = self.registry.all()
        if not panels:
            embed.add_field(
                name="Module",
                value="Noch keine Module registriert.",
                inline=False,
            )
        else:
            lines = [f"**{panel.label}** – {panel.description}" for panel in panels]
            embed.add_field(name="Module", value="\n".join(lines), inline=False)

        embed.set_footer(text="Kuhmuh Admin-Hub · V2")
        return embed

    # -------------------------
    # Slash Command
    # -------------------------
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    @app_commands.command(name="admin", description="Oeffnet bzw. aktualisiert das Kuhmuh Admin-Panel.")
    @app_commands.describe(aktion="Posten/Verschieben oder Refresh")
    @app_commands.choices(aktion=ACTION_CHOICES)
    async def admin_command(
        self,
        interaction: discord.Interaction,
        aktion: app_commands.Choice[str],
    ) -> None:
        if interaction.guild is None or interaction.guild.id != GUILD_ID:
            await interaction.response.send_message(
                "Dieser Command ist nur auf dem Kuhmuh-Server verfuegbar.",
                ephemeral=True,
            )
            return

        if not isinstance(interaction.user, discord.Member) or not self.is_authorized(interaction.user):
            await interaction.response.send_message(
                "Dafuer fehlen dir die erforderlichen Berechtigungen.",
                ephemeral=True,
            )
            return

        await interaction.response.defer(ephemeral=True)

        if aktion.value == "post":
            await self._post_or_move_panel(interaction)
        else:
            await self._refresh_panel(interaction)

    # -------------------------
    # Panel: Posten / Verschieben
    # -------------------------
    async def _post_or_move_panel(self, interaction: discord.Interaction) -> None:
        guild = interaction.guild
        channel = interaction.channel
        if guild is None or not isinstance(channel, discord.TextChannel):
            await interaction.followup.send(
                "Bitte in einem Text-Channel ausfuehren.",
                ephemeral=True,
            )
            return

        embed = self.build_main_embed()
        view = AdminHubView(self)

        channel_id = await self.config.guild(guild).panel_channel_id()
        message_id = await self.config.guild(guild).panel_message_id()

        if channel_id and message_id:
            old_channel = guild.get_channel(int(channel_id))

            if isinstance(old_channel, discord.TextChannel) and old_channel.id != channel.id:
                with contextlib.suppress(Exception):
                    old_message = await old_channel.fetch_message(int(message_id))
                    await old_message.delete()
            elif isinstance(old_channel, discord.TextChannel):
                try:
                    message = await old_channel.fetch_message(int(message_id))
                    await message.edit(embed=embed, view=view)
                    await interaction.followup.send("Admin-Panel aktualisiert.", ephemeral=True)
                    return
                except Exception:
                    pass

        new_message = await channel.send(embed=embed, view=view)
        await self.config.guild(guild).panel_channel_id.set(channel.id)
        await self.config.guild(guild).panel_message_id.set(new_message.id)
        await interaction.followup.send("Admin-Panel gepostet.", ephemeral=True)

    # -------------------------
    # Panel: Refresh
    # -------------------------
    async def _refresh_panel(self, interaction: discord.Interaction) -> None:
        guild = interaction.guild
        if guild is None:
            return

        channel_id = await self.config.guild(guild).panel_channel_id()
        message_id = await self.config.guild(guild).panel_message_id()
        if not channel_id or not message_id:
            await interaction.followup.send(
                "Es ist noch kein Admin-Panel gepostet. Nutze zuerst `Posten / Verschieben`.",
                ephemeral=True,
            )
            return

        channel = guild.get_channel(int(channel_id))
        if not isinstance(channel, discord.TextChannel):
            await interaction.followup.send(
                "Der gespeicherte Panel-Channel ist nicht mehr verfuegbar.",
                ephemeral=True,
            )
            return

        try:
            message = await channel.fetch_message(int(message_id))
            await message.edit(embed=self.build_main_embed(), view=AdminHubView(self))
            await interaction.followup.send("Admin-Panel aktualisiert.", ephemeral=True)
        except Exception:
            await interaction.followup.send(
                "Das Admin-Panel konnte nicht aktualisiert werden.",
                ephemeral=True,
            )
