from __future__ import annotations

import asyncio
import contextlib
import datetime as dt
import logging
from dataclasses import dataclass
from typing import Any

import discord
from discord import app_commands
from discord.ext.commands.view import StringView
from redbot.core import Config, commands

from ..registry import AdminPanel

GUILD_ID = 1198649628787212458
OWNER_ID = 359447597427064833
ADMIN_ROLE_ID = 1198650646786736240
OFFICIER_ROLE_ID = 1198652039312453723
LOG_CHANNEL_ID = 1460298038269575282

log = logging.getLogger("red.kuhmuh.adminhub.update")


@dataclass
class StepResult:
    name: str
    status: str
    summary: str
    details: str = ""


class CapturedMessage:
    __slots__ = ("content", "embeds")

    def __init__(self, content: str | None = None, embeds: list[discord.Embed] | None = None) -> None:
        self.content = content
        self.embeds = embeds or []


class CommandOutputCatcher:
    def __init__(self) -> None:
        self.messages: list[CapturedMessage] = []

    async def send(self, content: str | None = None, **kwargs: Any) -> CapturedMessage:
        embeds = []
        if kwargs.get("embed") is not None:
            embeds.append(kwargs["embed"])
        embeds.extend(kwargs.get("embeds") or [])
        message = CapturedMessage(content, embeds)
        self.messages.append(message)
        return message

    def render_text(self) -> str:
        parts: list[str] = []
        for message in self.messages:
            if message.content:
                parts.append(str(message.content))
            for embed in message.embeds:
                fields = "\n".join(f"{field.name}: {field.value}" for field in embed.fields)
                chunk = "\n".join(value for value in (embed.title, embed.description, fields) if value).strip()
                if chunk:
                    parts.append(chunk)
        return "\n".join(parts).strip()


class UpdatePanel:
    def __init__(self, bot) -> None:
        self.bot = bot
        self.config = Config.get_conf(self, identifier=946102221, force_registration=True)
        self.config.register_global(embed_detail_limit=400, stored_cogs={})
        self.update_lock = asyncio.Lock()
        self.panel = AdminPanel(
            key="kuhmuhupdate",
            label="KuhmuhUpdate",
            description="Cogs verwalten, aktualisieren und laden.",
            build_embed=self.build_embed,
            build_view=self.build_view,
            required_check=self.is_authorized,
        )

    def is_authorized(self, interaction: discord.Interaction) -> bool:
        user = interaction.user
        if user.id == OWNER_ID:
            return True
        role_ids = {role.id for role in getattr(user, "roles", ())}
        return bool(role_ids & {ADMIN_ROLE_ID, OFFICIER_ROLE_ID})

    async def get_stored_cogs(self) -> dict[str, dict[str, str]]:
        data = await self.config.stored_cogs()
        if not isinstance(data, dict):
            return {}
        result: dict[str, dict[str, str]] = {}
        for key, value in data.items():
            if not isinstance(key, str) or not isinstance(value, dict):
                continue
            cog_name = value.get("cog_name")
            repo_name = value.get("repo_name")
            if isinstance(cog_name, str) and isinstance(repo_name, str):
                result[key] = {"cog_name": cog_name, "repo_name": repo_name}
        return result

    async def build_embed(self, _interaction: discord.Interaction) -> discord.Embed:
        stored = await self.get_stored_cogs()
        embed = discord.Embed(
            title="KuhmuhUpdate",
            description="Cogs verwalten, aktualisieren und laden.",
            color=discord.Color.orange(),
        )
        if stored:
            lines = [
                f"• **{value['cog_name']}** → `{value['repo_name']}`"
                for _, value in sorted(stored.items(), key=lambda item: item[1]["cog_name"].casefold())
            ]
            embed.add_field(name="Gespeicherte Cogs", value="\n".join(lines), inline=False)
        else:
            embed.add_field(name="Gespeicherte Cogs", value="Keine Einträge vorhanden.", inline=False)
        embed.add_field(
            name="Aktionen",
            value="Cog auswählen und `Update` oder `Entfernen` verwenden. Neue Einträge über `Hinzufügen` anlegen.",
            inline=False,
        )
        return embed

    async def build_view(self, _interaction: discord.Interaction) -> discord.ui.View:
        return await UpdatePanelView.create(self)

    async def set_stored_cog(self, cog_name: str, repo_name: str) -> None:
        data = await self.get_stored_cogs()
        data[cog_name.strip().casefold()] = {
            "cog_name": cog_name.strip(),
            "repo_name": repo_name.strip(),
        }
        await self.config.stored_cogs.set(data)

    async def remove_stored_cog(self, key: str) -> bool:
        data = await self.get_stored_cogs()
        if key not in data:
            return False
        del data[key]
        await self.config.stored_cogs.set(data)
        return True

    async def invoke_command(self, interaction: discord.Interaction, name: str, arguments: str = "") -> tuple[bool, str]:
        command = self.bot.get_command(name)
        if command is None:
            return False, f"Command nicht gefunden: {name}"

        context = await commands.Context.from_interaction(interaction)
        context.prefix = "°"
        context.command = command
        context.view = StringView(arguments)
        context.invoked_with = name.split(" ")[0]
        catcher = CommandOutputCatcher()
        original_send = context.send
        context.send = catcher.send  # type: ignore[assignment]
        original_reply = getattr(context, "reply", None)
        if original_reply is not None:
            context.reply = catcher.send  # type: ignore[assignment]

        try:
            await command.invoke(context)
            return True, catcher.render_text()
        except Exception as exc:
            output = catcher.render_text()
            error = f"{type(exc).__name__}: {exc}"
            return False, f"{output}\n{error}".strip()
        finally:
            context.send = original_send  # type: ignore[assignment]
            if original_reply is not None:
                context.reply = original_reply  # type: ignore[assignment]

    async def run_update(self, interaction: discord.Interaction, key: str) -> None:
        stored = await self.get_stored_cogs()
        selected = stored.get(key)
        if selected is None:
            await interaction.response.send_message("Der ausgewählte Cog ist nicht mehr vorhanden.", ephemeral=True)
            return
        if self.update_lock.locked():
            await interaction.response.send_message("⏭️ Ein Update läuft bereits.", ephemeral=True)
            return
        if not isinstance(interaction.channel, discord.TextChannel):
            await interaction.response.send_message("Bitte in einem Text-Channel ausführen.", ephemeral=True)
            return

        cog_name = selected["cog_name"]
        repo_name = selected["repo_name"]
        placeholder = discord.Embed(
            title=f"Update: {cog_name}",
            description=f"Repo: **{repo_name}**\n\n⏳ Update läuft …",
        )
        public_message = await interaction.channel.send(embed=placeholder)
        await interaction.response.send_message("Das Update wurde gestartet.", ephemeral=True)

        async with self.update_lock:
            results: list[StepResult] = []
            ok, output = await self.invoke_command(interaction, "cog uninstall", cog_name)
            await self.log_output(interaction, f"[AdminHub Update] Uninstall {cog_name}", output)
            if ok or self._contains_not_installed(output):
                results.append(StepResult("Uninstall", "✅" if ok else "⚠️", "Deinstalliert." if ok else "Nicht installiert (weiter).", output))
            else:
                results.append(StepResult("Uninstall", "❌", "Fehler – Abbruch.", output))
                await self.finalize(public_message, cog_name, repo_name, results)
                return

            for step_name, command_name, arguments in (
                ("Repo Update", "repo update", repo_name),
                ("Install", "cog install", f"{repo_name} {cog_name}"),
                ("Load", "load", cog_name),
            ):
                ok, output = await self.invoke_command(interaction, command_name, arguments)
                await self.log_output(interaction, f"[AdminHub Update] {step_name} {cog_name}", output)
                results.append(StepResult(step_name, "✅" if ok else "❌", "Erfolgreich." if ok else "Fehler – Prozess beendet.", output))
                if not ok:
                    break

            await self.finalize(public_message, cog_name, repo_name, results)

    async def finalize(self, message: discord.Message, cog_name: str, repo_name: str, results: list[StepResult]) -> None:
        embed = discord.Embed(title=f"Update: {cog_name}", description=f"Repo: **{repo_name}**")
        limit = int(await self.config.embed_detail_limit() or 400)
        for result in results:
            detail = next((line.strip() for line in result.details.splitlines() if line.strip()), "")
            if len(detail) > limit:
                detail = detail[: max(0, limit - 1)] + "…"
            summary = f"{result.status} {result.summary}"
            if detail:
                summary += f"\n```text\n{detail}\n```"
            embed.add_field(name=result.name, value=summary, inline=False)
        with contextlib.suppress(Exception):
            await message.edit(embed=embed)

    async def log_output(self, interaction: discord.Interaction, title: str, text: str) -> None:
        if not text:
            return
        log.info("%s\n%s", title, text)
        if not interaction.guild or not LOG_CHANNEL_ID:
            return
        channel = interaction.guild.get_channel(LOG_CHANNEL_ID)
        if isinstance(channel, (discord.TextChannel, discord.Thread)):
            with contextlib.suppress(Exception):
                await channel.send(f"**{title}**\n```text\n{text[:1900]}\n```")

    @staticmethod
    def _contains_not_installed(text: str) -> bool:
        lowered = text.casefold()
        return any(value in lowered for value in ("not installed", "not found", "no such cog"))


class AddCogModal(discord.ui.Modal, title="Cog speichern"):
    cog_name = discord.ui.TextInput(label="Cog-Name", max_length=100)
    repo_name = discord.ui.TextInput(label="Repository-Name", max_length=100)

    def __init__(self, panel: UpdatePanel, view: "UpdatePanelView") -> None:
        super().__init__()
        self.panel = panel
        self.view = view

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await self.panel.set_stored_cog(self.cog_name.value, self.repo_name.value)
        await interaction.response.edit_message(
            embed=await self.panel.build_embed(interaction),
            view=await UpdatePanelView.create(self.panel),
        )


class UpdatePanelView(discord.ui.View):
    def __init__(self, panel: UpdatePanel, options: list[app_commands.Choice[str]]) -> None:
        super().__init__(timeout=None)
        self.panel = panel
        self.selected_key: str | None = None
        select = discord.ui.Select(
            placeholder="Gespeicherten Cog auswählen …",
            options=[discord.SelectOption(label=choice.name[:100], value=choice.value) for choice in options]
            or [discord.SelectOption(label="Keine Cogs gespeichert", value="__none__")],
            disabled=not options,
            custom_id="kuhmuh_adminhub_update_select",
        )
        select.callback = self.select_callback
        self.add_item(select)

        update_button = discord.ui.Button(label="Update", style=discord.ButtonStyle.success, custom_id="kuhmuh_adminhub_update_run")
        update_button.callback = self.update_callback
        self.add_item(update_button)

        add_button = discord.ui.Button(label="Hinzufügen", style=discord.ButtonStyle.primary, custom_id="kuhmuh_adminhub_update_add")
        add_button.callback = self.add_callback
        self.add_item(add_button)

        remove_button = discord.ui.Button(label="Entfernen", style=discord.ButtonStyle.danger, custom_id="kuhmuh_adminhub_update_remove")
        remove_button.callback = self.remove_callback
        self.add_item(remove_button)

    @classmethod
    async def create(cls, panel: UpdatePanel) -> "UpdatePanelView":
        stored = await panel.get_stored_cogs()
        options = [
            app_commands.Choice(name=f"{value['cog_name']} ({value['repo_name']})", value=key)
            for key, value in sorted(stored.items(), key=lambda item: item[1]["cog_name"].casefold())
        ][:25]
        return cls(panel, options)

    async def select_callback(self, interaction: discord.Interaction) -> None:
        self.selected_key = interaction.data["values"][0]  # type: ignore[index]
        await interaction.response.edit_message(view=self)

    async def update_callback(self, interaction: discord.Interaction) -> None:
        if not self.selected_key or self.selected_key == "__none__":
            await interaction.response.send_message("Bitte zuerst einen Cog auswählen.", ephemeral=True)
            return
        await self.panel.run_update(interaction, self.selected_key)

    async def add_callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_modal(AddCogModal(self.panel, self))

    async def remove_callback(self, interaction: discord.Interaction) -> None:
        if not self.selected_key or self.selected_key == "__none__":
            await interaction.response.send_message("Bitte zuerst einen Cog auswählen.", ephemeral=True)
            return
        removed = await self.panel.remove_stored_cog(self.selected_key)
        await interaction.response.edit_message(
            embed=await self.panel.build_embed(interaction),
            view=await UpdatePanelView.create(self.panel),
        )
        if not removed:
            await interaction.followup.send("Der Eintrag war nicht mehr vorhanden.", ephemeral=True)
