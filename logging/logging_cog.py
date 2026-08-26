from __future__ import annotations

import datetime as dt

import discord
from redbot.core import Config, app_commands, commands


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

ACTION_CHOICES = [
    app_commands.Choice(name="Konfiguration anzeigen", value="show"),
    app_commands.Choice(name="Zielchannel setzen", value="set"),
    app_commands.Choice(name="Bereich deaktivieren", value="disable"),
    app_commands.Choice(name="Zielchannel zurücksetzen", value="reset"),
    app_commands.Choice(name="Beispiel ausgeben", value="preview"),
]

LOG_CATEGORIES = ("message", "member", "server", "voice", "join_leave")
DEFAULT_GUILD = {"channels": {category: 0 for category in LOG_CATEGORIES}}


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
    identity = f"{username} · {user.id}"
    return f"{user.mention}\n{identity}"


def _channel_mention(channel: discord.abc.GuildChannel | discord.Thread | None) -> str:
    return channel.mention if channel is not None else "nicht verfuegbar"


def _changed_permissions(changes: list[tuple[str, str, str]]) -> str:
    return "\n".join(f"{label}: {before} → {after}" for label, before, after in changes)


def _bool_state(value: bool) -> str:
    return "✅" if value else "❌"


PERMISSION_LABELS = {
    "view_channel": "Kanal ansehen",
    "send_messages": "Nachrichten senden",
    "attach_files": "Dateien anhängen",
    "add_reactions": "Reaktionen hinzufügen",
    "connect": "Verbinden",
    "manage_messages": "Nachrichten verwalten",
    "mention_everyone": "Erwähnungen verwenden",
}


def _permission_label(name: str) -> str:
    return PERMISSION_LABELS.get(name, name.replace("_", " ").capitalize())


def _account_age(created_at: dt.datetime, now: dt.datetime | None = None) -> str:
    reference = now or discord.utils.utcnow()
    elapsed_days = max((reference - created_at).days, 0)
    years, remaining_days = divmod(elapsed_days, 365)
    months, days = divmod(remaining_days, 30)
    parts = []
    if years:
        parts.append(f"{years} Jahr" if years == 1 else f"{years} Jahre")
    if months:
        parts.append(f"{months} Monat" if months == 1 else f"{months} Monate")
    if days or not parts:
        parts.append(f"{days} Tag" if days == 1 else f"{days} Tage")
    return ", ".join(parts)


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
        self.config = Config.get_conf(self, identifier=0x4B55484D554C4F47, force_registration=True)
        self.config.register_guild(**DEFAULT_GUILD)
        self._handled_delete_ids: set[int] = set()
        self._startup_task = self.bot.loop.create_task(self._startup_guild_sync())

    async def _startup_guild_sync(self) -> None:
        await self.bot.wait_until_red_ready()
        await self.bot.wait_until_ready()
        await self.bot.tree.sync(guild=discord.Object(id=GUILD_ID))

    @app_commands.guilds(discord.Object(id=GUILD_ID))
    @app_commands.command(
        name="logging",
        description="Verwaltet die fuenf Discord-Logging-Bereiche.",
    )
    @app_commands.describe(
        action="Verwaltungsaktion",
        category="Logging-Bereich fuer die Aktion",
        channel="Zielchannel fuer den Bereich",
    )
    @app_commands.choices(action=ACTION_CHOICES, category=CATEGORY_CHOICES)
    async def logging_command(
        self,
        interaction: discord.Interaction,
        action: app_commands.Choice[str],
        category: app_commands.Choice[str] | None = None,
        channel: discord.TextChannel | None = None,
    ) -> None:
        if not self._is_authorized(interaction):
            await interaction.response.send_message(
                "Dafuer fehlen dir die erforderlichen Berechtigungen.",
                ephemeral=True,
            )
            return

        if interaction.guild is None:
            await interaction.response.send_message(
                "Die Logging-Verwaltung kann nur auf dem Kuhmuh-Server ausgefuehrt werden.",
                ephemeral=True,
            )
            return

        if action.value == "show":
            await self._show_configuration(interaction)
            return

        if category is None:
            await interaction.response.send_message(
                "Bitte waehle genau einen Logging-Bereich aus.", ephemeral=True
            )
            return

        if action.value == "preview" and category.value == "all":
            sent_categories = []
            for category_name in LOG_CATEGORIES:
                embeds = self._build_test_embeds(interaction, category_name)
                if await self._send_category_embeds(interaction.guild, category_name, embeds):
                    sent_categories.append(_category_label(category_name))
            result = ", ".join(sent_categories) if sent_categories else "keiner"
            await interaction.response.send_message(
                f"Beispiele ausgegeben fuer: {result}.", ephemeral=True
            )
            return

        if category.value == "all":
            await interaction.response.send_message(
                "Fuer diese Aktion muss ein einzelner Logging-Bereich gewaehlt werden.",
                ephemeral=True,
            )
            return

        if action.value == "set":
            if channel is None:
                await interaction.response.send_message(
                    "Zum Setzen muss ein Zielchannel angegeben werden.", ephemeral=True
                )
                return
            await self.config.guild(interaction.guild).channels.set(
                {**await self.config.guild(interaction.guild).channels(), category.value: channel.id}
            )
            await interaction.response.send_message(
                f"{_category_label(category.value)} wird jetzt nach {channel.mention} geloggt.",
                ephemeral=True,
            )
            return

        if action.value in {"disable", "reset"}:
            channels = await self.config.guild(interaction.guild).channels()
            channels[category.value] = 0
            await self.config.guild(interaction.guild).channels.set(channels)
            await interaction.response.send_message(
                f"{_category_label(category.value)} wurde deaktiviert.", ephemeral=True
            )
            return

        if action.value == "preview":
            embeds = self._build_test_embeds(interaction, category.value)
            sent = await self._send_category_embeds(interaction.guild, category.value, embeds)
            if sent:
                await interaction.response.send_message(
                    f"Beispiel fuer {_category_label(category.value)} wurde im konfigurierten Channel ausgegeben.",
                    ephemeral=True,
                )
            else:
                await interaction.response.send_message(
                    "Fuer diesen Bereich ist kein Zielchannel konfiguriert.", ephemeral=True
                )

    def _is_authorized(self, interaction: discord.Interaction) -> bool:
        user = interaction.user
        if user is None:
            return False
        if user.id == OWNER_ID:
            return True
        role_ids = {role.id for role in getattr(user, "roles", ())}
        return bool(role_ids & {ADMIN_ROLE_ID, OFFIZIER_ROLE_ID})

    async def _show_configuration(self, interaction: discord.Interaction) -> None:
        channels = await self.config.guild(interaction.guild).channels()
        embed = _embed("server", "Logging-Konfiguration")
        embed.description = "Jeder Bereich besitzt einen unabhängigen Zielchannel."
        for category in LOG_CATEGORIES:
            channel_id = channels.get(category, 0)
            target = f"<#{channel_id}>" if channel_id else "deaktiviert"
            embed.add_field(name=_category_label(category), value=target, inline=True)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    async def _send_category_embeds(
        self,
        guild: discord.Guild,
        category: str,
        embeds: list[discord.Embed],
    ) -> bool:
        channel_id = (await self.config.guild(guild).channels()).get(category, 0)
        channel = guild.get_channel(channel_id) if channel_id else None
        if not isinstance(channel, discord.TextChannel):
            return False
        await channel.send(embeds=embeds)
        return True

    async def send_log(
        self,
        guild: discord.Guild,
        category: str,
        embed: discord.Embed,
    ) -> bool:
        """Sendet spaetere Ereignis-Embeds ohne Fallback in einen anderen Bereich."""
        if category not in LOG_CATEGORIES:
            return False
        return await self._send_category_embeds(guild, category, [embed])

    async def _audit_actor(
        self,
        guild: discord.Guild,
        action: discord.AuditLogAction,
        target_id: int,
        *,
        max_age_seconds: int = 15,
    ) -> discord.User | discord.Member | None:
        now = discord.utils.utcnow()
        try:
            async for entry in guild.audit_logs(limit=10, action=action):
                if entry.target is None or getattr(entry.target, "id", None) != target_id:
                    continue
                if (now - entry.created_at).total_seconds() > max_age_seconds:
                    continue
                return entry.user
        except (discord.Forbidden, discord.HTTPException):
            return None
        return None

    @commands.Cog.listener()
    async def on_raw_message_delete(self, payload: discord.RawMessageDeleteEvent) -> None:
        """Loggt geloeschte Nachrichten, sofern der Message-Bereich konfiguriert ist."""
        if payload.guild_id != GUILD_ID:
            return

        if payload.message_id in self._handled_delete_ids:
            return

        channels = await self.config.guild_from_id(GUILD_ID).channels()
        log_channel_id = channels.get("message", 0)
        if not log_channel_id or payload.channel_id == log_channel_id:
            return

        guild = self.bot.get_guild(GUILD_ID)
        if guild is None:
            return

        cached_message = payload.cached_message
        embed = _embed("message", "Nachricht gelöscht")
        if cached_message is not None and cached_message.author is not None:
            embed.add_field(name="Autor", value=_user_lines(cached_message.author), inline=True)
        else:
            embed.add_field(name="Autor", value="nicht verfügbar (Nachricht nicht im Cache)", inline=True)
        embed.add_field(name="Channel", value=f"<#${payload.channel_id}>".replace("$", ""), inline=True)
        content = cached_message.content if cached_message is not None else "nicht verfügbar"
        embed.add_field(name="Ursprünglicher Inhalt", value=content[:1020] or "(leer)", inline=False)
        if cached_message is not None and cached_message.attachments:
            attachments = "\n".join(
                f"`{attachment.filename}` ({attachment.url})"
                for attachment in cached_message.attachments
            )
            embed.add_field(name="Anhänge", value=attachments[:1020], inline=False)
        embed.add_field(name="Nachricht", value=f"`{payload.message_id}`", inline=True)
        embed.add_field(name="Zeit", value=_timestamp(), inline=True)
        if await self.send_log(guild, "message", embed):
            self._handled_delete_ids.add(payload.message_id)

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message) -> None:
        """Fallback fuer geloeschte Nachrichten, die im Cache vorhanden waren."""
        if message.guild is None or message.guild.id != GUILD_ID:
            return
        if message.id in self._handled_delete_ids:
            return

        embed = _embed("message", "Nachricht gelöscht")
        embed.add_field(name="Autor", value=_user_lines(message.author), inline=True)
        embed.add_field(name="Channel", value=message.channel.mention, inline=True)
        embed.add_field(name="Ursprünglicher Inhalt", value=message.content[:1020] or "(leer)", inline=False)
        if message.attachments:
            attachments = "\n".join(
                f"`{attachment.filename}` ({attachment.url})"
                for attachment in message.attachments
            )
            embed.add_field(name="Anhänge", value=attachments[:1020], inline=False)
        embed.add_field(name="Nachricht", value=f"`{message.id}`", inline=True)
        embed.add_field(name="Zeit", value=_timestamp(), inline=True)
        if await self.send_log(message.guild, "message", embed):
            self._handled_delete_ids.add(message.id)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent) -> None:
        await self._log_reaction(payload, "Reaktion hinzugefügt")

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent) -> None:
        await self._log_reaction(payload, "Reaktion entfernt")

    async def _log_reaction(
        self,
        payload: discord.RawReactionActionEvent,
        title: str,
    ) -> None:
        if payload.guild_id != GUILD_ID or payload.user_id == self.bot.user.id:
            return
        guild = self.bot.get_guild(GUILD_ID)
        channel = guild.get_channel(payload.channel_id) if guild is not None else None
        if guild is None or channel is None:
            return
        user = payload.member or self.bot.get_user(payload.user_id)
        message = None
        try:
            message = await channel.fetch_message(payload.message_id)
        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
            pass
        if user is None:
            user_text = f"<@{payload.user_id}>\nUnbekannter Nutzer · {payload.user_id}"
        else:
            user_text = _user_lines(user)
        embed = _embed("message", title)
        embed.add_field(name="Nutzer", value=user_text, inline=True)
        embed.add_field(name="Emoji", value=str(payload.emoji), inline=True)
        embed.add_field(name="Channel", value=channel.mention, inline=True)
        message_url = f"https://discord.com/channels/{GUILD_ID}/{payload.channel_id}/{payload.message_id}"
        embed.add_field(
            name="Nachricht",
            value=f"`{payload.message_id}`\n[Zur Nachricht]({message.jump_url if message else message_url})",
            inline=False,
        )
        if message is not None:
            embed.add_field(name="Nachrichtenautor", value=_user_lines(message.author), inline=False)
        embed.add_field(name="Zeit", value=_timestamp(), inline=False)
        await self.send_log(guild, "message", embed)

    @commands.Cog.listener()
    async def on_message_edit(
        self,
        before: discord.Message,
        after: discord.Message,
    ) -> None:
        if before.guild is None or before.guild.id != GUILD_ID:
            return
        if before.content == after.content:
            return
        embed = _embed("message", "Nachricht bearbeitet")
        embed.add_field(name="Nutzer", value=_user_lines(after.author), inline=True)
        embed.add_field(name="Channel", value=after.channel.mention, inline=True)
        embed.add_field(
            name="Nachricht",
            value=f"`{after.id}`\n[Zur Nachricht]({after.jump_url})",
            inline=False,
        )
        embed.add_field(name="Vorher", value=before.content[:1020] or "(leer)", inline=True)
        embed.add_field(name="Nachher", value=after.content[:1020] or "(leer)", inline=True)
        embed.add_field(name="Zeit", value=_timestamp(), inline=False)
        await self.send_log(before.guild, "message", embed)

    @commands.Cog.listener()
    async def on_member_update(
        self,
        before: discord.Member,
        after: discord.Member,
    ) -> None:
        if after.guild.id != GUILD_ID:
            return
        before_roles = {role.id: role for role in before.roles}
        after_roles = {role.id: role for role in after.roles}
        added_roles = [after_roles[role_id] for role_id in after_roles.keys() - before_roles.keys()]
        removed_roles = [before_roles[role_id] for role_id in before_roles.keys() - after_roles.keys()]
        for role, title in [(role, "Rolle hinzugefügt") for role in added_roles] + [
            (role, "Rolle entfernt") for role in removed_roles
        ]:
            embed = _embed("member", title)
            embed.add_field(name="Mitglied", value=_user_lines(after), inline=False)
            embed.add_field(name="Rolle", value=role.mention, inline=True)
            actor = await self._audit_actor(
                after.guild,
                discord.AuditLogAction.member_role_update,
                after.id,
            )
            if actor is not None:
                embed.add_field(name="Ausgeführt von", value=_user_lines(actor), inline=True)
            embed.add_field(name="Zeit", value=_timestamp(), inline=True)
            await self.send_log(after.guild, "member", embed)

        if before.nick != after.nick:
            embed = _embed("member", "Server-Nickname geändert")
            embed.add_field(name="Mitglied", value=_user_lines(after), inline=False)
            embed.add_field(name="Vorher", value=before.nick or "kein Nickname", inline=True)
            embed.add_field(name="Nachher", value=after.nick or "kein Nickname", inline=True)
            embed.add_field(name="Zeit", value=_timestamp(), inline=False)
            await self.send_log(after.guild, "member", embed)

        if before.premium_since != after.premium_since:
            title = "Server-Boost gestartet" if after.premium_since else "Server-Boost beendet"
            embed = _embed("member", title)
            embed.add_field(name="Nutzer", value=_user_lines(after), inline=False)
            embed.add_field(name="Boosts", value=str(after.guild.premium_subscription_count or 0), inline=True)
            if after.guild.premium_tier:
                embed.add_field(name="Boost-Level", value=str(after.guild.premium_tier), inline=True)
            embed.add_field(name="Zeit", value=_timestamp(), inline=False)
            await self.send_log(after.guild, "member", embed)

    @commands.Cog.listener()
    async def on_user_update(self, before: discord.User, after: discord.User) -> None:
        name_changed = before.name != after.name
        global_name_changed = before.global_name != after.global_name
        avatar_changed = before.avatar != after.avatar
        if not (name_changed or global_name_changed or avatar_changed):
            return
        guild = self.bot.get_guild(GUILD_ID)
        member = guild.get_member(after.id) if guild is not None else None
        if guild is None or member is None:
            return

        changed_values = []
        if name_changed:
            changed_values.append(("Discord-Username", before.name, after.name))
        if global_name_changed:
            changed_values.append(
                (
                    "Globaler Anzeigename",
                    before.global_name or "nicht gesetzt",
                    after.global_name or "nicht gesetzt",
                )
            )
        embed = _embed("member", "Discord-Profil geändert")
        embed.add_field(name="Mitglied", value=_user_lines(after), inline=False)
        for label, old_value, new_value in changed_values:
            embed.add_field(name=f"{label} vorher", value=old_value, inline=True)
            embed.add_field(name=f"{label} nachher", value=new_value, inline=True)
        if avatar_changed:
            if after.avatar:
                embed.set_image(url=after.avatar.url)
                embed.set_thumbnail(url=after.avatar.url)
            embed.add_field(name="Avatar", value="Neuer Avatar direkt im Embed", inline=False)
        embed.add_field(name="Zeit", value=_timestamp(), inline=False)
        await self.send_log(guild, "member", embed)

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel) -> None:
        if channel.guild.id != GUILD_ID:
            return
        embed = _embed("server", "Channel erstellt")
        embed.add_field(name="Channel", value=channel.mention, inline=True)
        embed.add_field(name="Name", value=channel.name, inline=True)
        embed.add_field(name="Zeit", value=_timestamp(), inline=False)
        await self.send_log(channel.guild, "server", embed)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel) -> None:
        if channel.guild.id != GUILD_ID:
            return
        embed = _embed("server", "Channel gelöscht")
        embed.add_field(name="Letzter Name", value=channel.name, inline=True)
        embed.add_field(name="Channel-ID", value=f"`{channel.id}`", inline=True)
        embed.add_field(name="Zeit", value=_timestamp(), inline=False)
        await self.send_log(channel.guild, "server", embed)

    @commands.Cog.listener()
    async def on_invite_create(self, invite: discord.Invite) -> None:
        if invite.guild is None or invite.guild.id != GUILD_ID:
            return
        embed = _embed("server", "Einladung erstellt")
        embed.add_field(name="Einladung", value=f"discord.gg/{invite.code}", inline=True)
        if invite.channel is not None:
            embed.add_field(name="Channel", value=invite.channel.mention, inline=True)
        if invite.inviter is not None:
            embed.add_field(name="Erstellt von", value=_user_lines(invite.inviter), inline=False)
        if invite.max_uses:
            embed.add_field(name="Maximale Nutzungen", value=str(invite.max_uses), inline=True)
        if invite.max_age:
            embed.add_field(name="Gültigkeit", value=f"{invite.max_age // 3600} Stunden", inline=True)
        embed.add_field(name="Zeit", value=_timestamp(), inline=False)
        await self.send_log(invite.guild, "server", embed)

    @commands.Cog.listener()
    async def on_guild_role_create(self, role: discord.Role) -> None:
        if role.guild.id != GUILD_ID:
            return
        embed = _embed("server", "Rolle erstellt")
        embed.add_field(name="Rolle", value=role.mention, inline=True)
        embed.add_field(name="Name", value=role.name, inline=True)
        actor = await self._audit_actor(role.guild, discord.AuditLogAction.role_create, role.id)
        if actor is not None:
            embed.add_field(name="Erstellt von", value=_user_lines(actor), inline=False)
        embed.add_field(name="Zeit", value=_timestamp(), inline=False)
        await self.send_log(role.guild, "server", embed)

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role: discord.Role) -> None:
        if role.guild.id != GUILD_ID:
            return
        embed = _embed("server", "Rolle gelöscht")
        embed.add_field(name="Letzter Name", value=role.name, inline=True)
        embed.add_field(name="Rollen-ID", value=f"`{role.id}`", inline=True)
        actor = await self._audit_actor(role.guild, discord.AuditLogAction.role_delete, role.id)
        if actor is not None:
            embed.add_field(name="Gelöscht von", value=_user_lines(actor), inline=False)
        embed.add_field(name="Zeit", value=_timestamp(), inline=False)
        await self.send_log(role.guild, "server", embed)

    @commands.Cog.listener()
    async def on_guild_role_update(self, before: discord.Role, after: discord.Role) -> None:
        if after.guild.id != GUILD_ID:
            return
        changes = []
        if before.name != after.name:
            changes.append(("Name", before.name, after.name))
        if before.color != after.color:
            changes.append(("Farbe", str(before.color), str(after.color)))
        if before.position != after.position:
            changes.append(("Position", str(before.position), str(after.position)))
        if before.mentionable != after.mentionable:
            changes.append(("Erwähnbar", _bool_state(before.mentionable), _bool_state(after.mentionable)))
        if before.hoist != after.hoist:
            changes.append(("Separat anzeigen", _bool_state(before.hoist), _bool_state(after.hoist)))
        if before.permissions != after.permissions:
            changes.extend(self._permission_changes(before.permissions, after.permissions))
        if not changes:
            return
        embed = _embed("server", "Rolle geändert")
        embed.add_field(name="Rolle", value=after.mention, inline=False)
        embed.add_field(
            name="Änderungen",
            value="\n".join(f"{label}: {old} → {new}" for label, old, new in changes)[:1020],
            inline=False,
        )
        actor = await self._audit_actor(after.guild, discord.AuditLogAction.role_update, after.id)
        if actor is not None:
            embed.add_field(name="Geändert von", value=_user_lines(actor), inline=True)
        embed.add_field(name="Zeit", value=_timestamp(), inline=True)
        await self.send_log(after.guild, "server", embed)

    @commands.Cog.listener()
    async def on_invite_delete(self, invite: discord.Invite) -> None:
        if invite.guild is None or invite.guild.id != GUILD_ID:
            return
        embed = _embed("server", "Einladung gelöscht")
        embed.add_field(name="Einladung", value=f"discord.gg/{invite.code}", inline=True)
        if invite.channel is not None:
            embed.add_field(name="Channel", value=invite.channel.mention, inline=True)
        if invite.inviter is not None:
            embed.add_field(name="Ursprünglicher Ersteller", value=_user_lines(invite.inviter), inline=False)
        if invite.max_uses:
            embed.add_field(name="Nutzungslimit", value=str(invite.max_uses), inline=True)
        if invite.max_age:
            embed.add_field(name="Ablaufzeit", value=f"{invite.max_age // 3600} Stunden", inline=True)
        embed.add_field(name="Zeit", value=_timestamp(), inline=False)
        await self.send_log(invite.guild, "server", embed)

    @commands.Cog.listener()
    async def on_guild_channel_update(
        self,
        before: discord.abc.GuildChannel,
        after: discord.abc.GuildChannel,
    ) -> None:
        if after.guild.id != GUILD_ID:
            return
        if before.name != after.name:
            embed = _embed("server", "Channel umbenannt")
            embed.add_field(name="Channel", value=after.mention, inline=False)
            embed.add_field(name="Vorher", value=before.name, inline=True)
            embed.add_field(name="Nachher", value=after.name, inline=True)
            embed.add_field(name="Zeit", value=_timestamp(), inline=False)
            await self.send_log(after.guild, "server", embed)

        channel_changes = []
        before_category = getattr(before.category, "name", None)
        after_category = getattr(after.category, "name", None)
        if before_category != after_category:
            channel_changes.append(("Kategorie", before_category or "keine", after_category or "keine"))
        if getattr(before, "topic", None) != getattr(after, "topic", None):
            channel_changes.append(("Thema", before.topic or "leer", after.topic or "leer"))
        if getattr(before, "slowmode_delay", 0) != getattr(after, "slowmode_delay", 0):
            channel_changes.append(("Slowmode", f"{before.slowmode_delay} Sekunden", f"{after.slowmode_delay} Sekunden"))
        if getattr(before, "nsfw", False) != getattr(after, "nsfw", False):
            channel_changes.append(("NSFW", _bool_state(before.nsfw), _bool_state(after.nsfw)))
        if channel_changes:
            embed = _embed("server", "Channel geändert")
            embed.add_field(name="Channel", value=after.mention, inline=False)
            embed.add_field(
                name="Änderungen",
                value="\n".join(f"{label}: {old} → {new}" for label, old, new in channel_changes)[:1020],
                inline=False,
            )
            actor = await self._audit_actor(after.guild, discord.AuditLogAction.channel_update, after.id)
            if actor is not None:
                embed.add_field(name="Geändert von", value=_user_lines(actor), inline=True)
            embed.add_field(name="Zeit", value=_timestamp(), inline=True)
            await self.send_log(after.guild, "server", embed)

        before_overwrites = getattr(before, "overwrites", {})
        after_overwrites = getattr(after, "overwrites", {})
        changes = []
        for target in set(before_overwrites) | set(after_overwrites):
            old = before_overwrites.get(target, discord.PermissionOverwrite())
            new = after_overwrites.get(target, discord.PermissionOverwrite())
            for label, old_state, new_state in self._overwrite_changes(old, new):
                changes.append((target, label, old_state, new_state))
        for target, label, old_state, new_state in changes:
            embed = _embed("server", "Channel-Rechte geändert")
            embed.add_field(name="Channel", value=after.mention, inline=True)
            embed.add_field(name="Betroffen", value=target.mention, inline=True)
            embed.add_field(
                name="Geänderte Permission",
                value=f"{label}: {old_state} → {new_state}",
                inline=False,
            )
            actor = await self._audit_actor(after.guild, discord.AuditLogAction.channel_update, after.id)
            if actor is not None:
                embed.add_field(name="Geändert von", value=_user_lines(actor), inline=True)
            embed.add_field(name="Zeit", value=_timestamp(), inline=False)
            await self.send_log(after.guild, "server", embed)

    @commands.Cog.listener()
    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ) -> None:
        if member.guild.id != GUILD_ID:
            return
        title = None
        details = []
        if before.channel != after.channel:
            if before.channel is None:
                title, details = "Voice-Channel beigetreten", [("Channel", after.channel.mention)]
            elif after.channel is None:
                title, details = "Voice-Channel verlassen", [("Channel", before.channel.mention)]
            else:
                title = "Voice-Channel gewechselt"
                details = [("Vorher", before.channel.mention), ("Nachher", after.channel.mention)]
        else:
            state_labels = (
                ("self_mute", "Self Mute"),
                ("self_deaf", "Self Deaf"),
                ("mute", "Server Mute"),
                ("deaf", "Server Deaf"),
                ("self_stream", "Stream"),
                ("self_video", "Kamera / Video"),
            )
            for attribute, label in state_labels:
                old_value = getattr(before, attribute)
                new_value = getattr(after, attribute)
                if old_value != new_value:
                    title = f"{label} {'aktiviert' if new_value else 'deaktiviert'}"
                    break
        if title is None:
            return
        embed = _embed("voice", title)
        embed.add_field(name="Mitglied", value=_user_lines(member), inline=False)
        for label, value in details:
            embed.add_field(name=label, value=value, inline=True)
        embed.add_field(name="Zeit", value=_timestamp(), inline=False)
        await self.send_log(member.guild, "voice", embed)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        if member.guild.id != GUILD_ID:
            return
        embed = _embed("join_leave", "Mitglied beigetreten")
        embed.add_field(name="Nutzer", value=_user_lines(member), inline=False)
        embed.add_field(name="Account erstellt", value=_timestamp(member.created_at), inline=True)
        embed.add_field(name="Account-Alter", value=_account_age(member.created_at), inline=True)
        embed.add_field(name="Server beigetreten", value=_timestamp(member.joined_at), inline=True)
        embed.add_field(name="Mitglieder", value=str(member.guild.member_count or "unbekannt"), inline=True)
        avatar = getattr(member, "display_avatar", None)
        if avatar:
            embed.set_thumbnail(url=avatar.url)
        await self.send_log(member.guild, "join_leave", embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member) -> None:
        if member.guild.id != GUILD_ID:
            return
        left_at = discord.utils.utcnow()
        embed = _embed("join_leave", "Mitglied verlassen")
        embed.add_field(name="Letzter Nutzer", value=_user_lines(member), inline=False)
        embed.add_field(name="Server beigetreten", value=_timestamp(member.joined_at), inline=True)
        embed.add_field(name="Server verlassen", value=_timestamp(left_at), inline=True)
        embed.add_field(name="Letzte Rollen", value=" ".join(role.mention for role in member.roles[1:]) or "keine", inline=False)
        embed.add_field(name="Mitglieder", value=str(max((member.guild.member_count or 1) - 1, 0)), inline=True)
        avatar = getattr(member, "display_avatar", None)
        if avatar:
            embed.set_thumbnail(url=avatar.url)
        await self.send_log(member.guild, "join_leave", embed)

    @staticmethod
    def _permission_state(overwrite: discord.PermissionOverwrite, name: str) -> str:
        value = getattr(overwrite, name)
        if value is True:
            return "✅"
        if value is False:
            return "❌"
        return "➖"

    @staticmethod
    def _overwrite_changes(
        before: discord.PermissionOverwrite,
        after: discord.PermissionOverwrite,
    ) -> list[tuple[str, str, str]]:
        changes = []
        for permission_name in discord.Permissions.VALID_FLAGS:
            old_state = LoggingCog._permission_state(before, permission_name)
            new_state = LoggingCog._permission_state(after, permission_name)
            if old_state != new_state:
                changes.append((_permission_label(permission_name), old_state, new_state))
        return changes

    @staticmethod
    def _permission_changes(
        before: discord.Permissions,
        after: discord.Permissions,
    ) -> list[tuple[str, str, str]]:
        changes = []
        for permission_name in discord.Permissions.VALID_FLAGS:
            old_value = getattr(before, permission_name)
            new_value = getattr(after, permission_name)
            if old_value != new_value:
                changes.append(
                    (
                        _permission_label(permission_name),
                        _bool_state(old_value),
                        _bool_state(new_value),
                    )
                )
        return changes

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