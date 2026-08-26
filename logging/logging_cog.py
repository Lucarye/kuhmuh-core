from __future__ import annotations

import datetime as dt

import discord
from redbot.core import app_commands, commands


GUILD_ID = 1198649628787212458
OWNER_ID = 359447597427064833
ADMIN_ROLE_ID = 1198650646786736240
OFFIZIER_ROLE_ID = 1198652039312453723
TEST_ROLE_ID = 1445018518562017373

LOG_COLORS = {
    "message": discord.Color.blurple(),
    "member": discord.Color.green(),
    "server": discord.Color.orange(),
    "voice": discord.Color.teal(),
    "join_leave": discord.Color.gold(),
}

CATEGORY_CHOICES = [
    app_commands.Choice(name="Alle Bereiche", value="all"),
    app_commands.Choice(name="Message", value="message"),
    app_commands.Choice(name="Member", value="member"),
    app_commands.Choice(name="Server", value="server"),
    app_commands.Choice(name="Voice", value="voice"),
    app_commands.Choice(name="Join-/Leave", value="join_leave"),
]


def _category_label(value: str) -> str:
    return next(
        (choice.name for choice in CATEGORY_CHOICES if choice.value == value),
        value,
    )


def _timestamp(value: dt.datetime | None = None) -> str:
    value = value or discord.utils.utcnow()
    return f"{discord.utils.format_dt(value, style='F')} ({discord.utils.format_dt(value, style='R')})"


def _user_lines(user: discord.abc.User) -> str:
    username = getattr(user, "name", "unbekannt")
    display_name = getattr(user, "display_name", username)
    identity = f"{username} · {user.id}"
    if display_name != username:
        identity = f"{display_name} · {identity}"
    return f"{user.mention}\n{identity}"


def _channel_mention(channel: discord.abc.GuildChannel | discord.Thread | None) -> str:
    return channel.mention if channel is not None else "nicht verfuegbar"


def _changed_permissions(changes: list[tuple[str, str, str]]) -> str:
    return "\n".join(f"{label}: {before} → {after}" for label, before, after in changes)


def _embed(category: str, title: str, description: str = "") -> discord.Embed:
    embed = discord.Embed(
        title=title,
        description=description or None,
        color=LOG_COLORS[category],
        timestamp=discord.utils.utcnow(),
    )
    embed.set_footer(text=f"Kuhmuh V2 · {category.replace('_', ' ').title()}")
    return embed


class LoggingCog(commands.Cog):
    """Visuelles Grundgeruest fuer die spaeteren Discord-Logs."""

    def __init__(self, bot) -> None:
        self.bot = bot
        self._startup_task = self.bot.loop.create_task(self._startup_guild_sync())

    async def _startup_guild_sync(self) -> None:
        await self.bot.wait_until_red_ready()
        await self.bot.wait_until_ready()
        await self.bot.tree.sync(guild=discord.Object(id=GUILD_ID))

    @app_commands.guilds(discord.Object(id=GUILD_ID))
    @app_commands.command(
        name="logging_test",
        description="Sendet visuelle Test-Embeds fuer das Logging.",
    )
    @app_commands.describe(category="Ein Bereich oder alle fuenf Bereiche")
    @app_commands.choices(category=CATEGORY_CHOICES)
    async def logging_test(
        self,
        interaction: discord.Interaction,
        category: str,
    ) -> None:
        if not self._is_authorized(interaction):
            await interaction.response.send_message(
                "Dafuer fehlen dir die erforderlichen Berechtigungen.",
                ephemeral=True,
            )
            return

        if interaction.guild is None or interaction.user is None:
            await interaction.response.send_message(
                "Der Test kann nur auf dem Kuhmuh-Server ausgefuehrt werden.",
                ephemeral=True,
            )
            return

        embeds = self._build_test_embeds(interaction, category)
        await interaction.response.send_message(
            content=f"{len(embeds)} Logging-Test-Embed(s) fuer **{_category_label(category)}**.",
            embeds=embeds,
        )

    def _is_authorized(self, interaction: discord.Interaction) -> bool:
        user = interaction.user
        if user is None:
            return False
        if user.id == OWNER_ID:
            return True
        role_ids = {role.id for role in getattr(user, "roles", ())}
        return bool(role_ids & {ADMIN_ROLE_ID, OFFIZIER_ROLE_ID, TEST_ROLE_ID})

    def _build_test_embeds(
        self,
        interaction: discord.Interaction,
        category: str,
    ) -> list[discord.Embed]:
        if category == "all":
            embeds: list[discord.Embed] = []
            for category_name in ("message", "member", "server", "voice", "join_leave"):
                embeds.extend(self._build_category_embeds(interaction, category_name))
            return embeds
        return self._build_category_embeds(interaction, category)

    def _build_category_embeds(
        self,
        interaction: discord.Interaction,
        category: str,
    ) -> list[discord.Embed]:
        builder = getattr(self, f"_{category}_test")
        result = builder(interaction)
        return result if isinstance(result, list) else [result]

    def _message_test(self, interaction: discord.Interaction) -> discord.Embed:
        embed = _embed("message", "Nachricht bearbeitet", "Eine visuelle Beispielausgabe.")
        embed.add_field(name="Nutzer", value=_user_lines(interaction.user), inline=True)
        embed.add_field(name="Channel", value=_channel_mention(interaction.channel), inline=True)
        embed.add_field(name="Nachricht", value="`987654321012345678`\n[Zur Nachricht](https://discord.com/channels/1198649628787212458/1199322485297000528/987654321012345678)", inline=False)
        embed.add_field(name="Vorher", value="Suche startet um 19:00", inline=True)
        embed.add_field(name="Nachher", value="Suche startet um 19:30", inline=True)
        embed.add_field(name="Zeit", value=_timestamp(), inline=False)
        return embed

    def _member_test(self, interaction: discord.Interaction) -> discord.Embed:
        embed = _embed("member", "Rolle hinzugefügt")
        role = self._test_role(interaction.guild)
        embed.add_field(name="Mitglied", value=_user_lines(interaction.user), inline=False)
        embed.add_field(name="Rolle", value=role.mention if role else f"<@&{TEST_ROLE_ID}>", inline=True)
        embed.add_field(name="Ausgeführt von", value=_user_lines(interaction.user), inline=True)
        embed.add_field(name="Zeit", value=_timestamp(), inline=False)
        return embed

    def _server_test(self, interaction: discord.Interaction) -> discord.Embed:
        embed = _embed("server", "Channel-Rechte geändert")
        embed.add_field(name="Channel", value=_channel_mention(interaction.channel), inline=True)
        embed.add_field(name="Ziel", value=f"<@&{TEST_ROLE_ID}>", inline=True)
        embed.add_field(name="Geänderte Permissions", value=_changed_permissions([
            ("Nachrichten senden", "✅", "❌"),
            ("Dateien anhängen", "➖", "✅"),
            ("Reaktionen hinzufügen", "❌", "➖"),
        ]), inline=False)
        embed.add_field(name="Ausgeführt von", value=_user_lines(interaction.user), inline=True)
        embed.add_field(name="Zeit", value=_timestamp(), inline=True)
        return embed

    def _voice_test(self, interaction: discord.Interaction) -> discord.Embed:
        embed = _embed("voice", "Voice-Channel gewechselt")
        embed.add_field(name="Mitglied", value=_user_lines(interaction.user), inline=False)
        embed.add_field(name="Vorher", value="🔊 <#1199322485297000528>", inline=True)
        embed.add_field(name="Nachher", value="🔊 <#1486128654332203140>", inline=True)
        embed.add_field(name="Zeit", value=_timestamp(), inline=False)
        return embed

    def _join_leave_test(self, interaction: discord.Interaction) -> list[discord.Embed]:
        now = discord.utils.utcnow()
        account_created = now - dt.timedelta(days=420)
        joined = now - dt.timedelta(days=37, hours=4)
        join = _embed("join_leave", "Mitglied beigetreten", "Beispiel fuer den spaeteren Join-Log.")
        join.add_field(name="Nutzer", value=_user_lines(interaction.user), inline=False)
        join.add_field(name="Account erstellt", value=_timestamp(account_created), inline=True)
        join.add_field(name="Server beigetreten", value=_timestamp(joined), inline=True)
        join.add_field(name="Account-Alter", value="420 Tage", inline=True)
        join.add_field(name="Mitglieder", value="1.234", inline=True)
        join.add_field(name="Invite", value="`kuhmuh-test`\nErsteller: @Einladender Nutzer", inline=True)
        avatar = getattr(interaction.user, "display_avatar", None)
        if avatar:
            join.set_thumbnail(url=avatar.url)

        leave = _embed("join_leave", "Mitglied verlassen", "Beispiel fuer den spaeteren Leave-Log.")
        leave.add_field(name="Letzter Nutzername", value=_user_lines(interaction.user), inline=False)
        leave.add_field(name="Beigetreten", value=_timestamp(joined), inline=True)
        leave.add_field(name="Verlassen", value=_timestamp(now), inline=True)
        leave.add_field(name="Mitgliedsdauer", value="37 Tage, 4 Stunden", inline=True)
        leave.add_field(name="Letzte Rollen", value=f"<@&{TEST_ROLE_ID}>", inline=True)
        leave.add_field(name="Mitglieder", value="1.233", inline=True)
        if avatar:
            leave.set_thumbnail(url=avatar.url)
        return [join, leave]

    @staticmethod
    def _test_role(guild: discord.Guild | None) -> discord.Role | None:
        if guild is None:
            return None
        return guild.get_role(TEST_ROLE_ID)