from __future__ import annotations

import asyncio
import contextlib
import logging
from dataclasses import dataclass
from typing import Any

import discord
from discord.ext import commands
from discord.ext.commands.view import StringView
from redbot.core import Config


LOG = logging.getLogger("red.kuhmuh.adminhub.kuhmuhupdate")
CONFIG_IDENTIFIER = 946102221


@dataclass
class CapturedMessage:
    content: str | None = None
    embeds: list[discord.Embed] | None = None


@dataclass
class StepResult:
    name: str
    status: str
    summary: str
    details: str = ""


class CommandOutputCatcher:
    def __init__(self) -> None:
        self.messages: list[CapturedMessage] = []

    async def send(self, content: str | None = None, **kwargs: Any) -> CapturedMessage:
        embeds: list[discord.Embed] = []
        if kwargs.get("embed") is not None:
            embeds.append(kwargs["embed"])
        embeds.extend(kwargs.get("embeds") or [])
        message = CapturedMessage(content=content, embeds=embeds)
        self.messages.append(message)
        return message

    def render_text(self) -> str:
        parts: list[str] = []
        for message in self.messages:
            if message.content:
                parts.append(str(message.content))
            for embed in message.embeds or []:
                fields = "\n".join(f"{field.name}: {field.value}" for field in embed.fields)
                chunk = "\n".join(value for value in (embed.title, embed.description, fields) if value)
                if chunk.strip():
                    parts.append(chunk.strip())
        return "\n".join(parts).strip()


class KuhmuhUpdateService:
    """V2-Service für gespeicherte Cog-Updates über Redbot-Prefix-Commands."""

    def __init__(self, bot) -> None:
        self.bot = bot
        self.config = Config.get_conf(
            self,
            identifier=CONFIG_IDENTIFIER,
            force_registration=True,
        )
        self.config.register_global(embed_detail_limit=400, stored_cogs={})
        self.update_lock = asyncio.Lock()

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

    async def add_cog(self, cog_name: str, repo_name: str) -> None:
        data = await self.get_stored_cogs()
        data[cog_name.strip().casefold()] = {
            "cog_name": cog_name.strip(),
            "repo_name": repo_name.strip(),
        }
        await self.config.stored_cogs.set(data)

    async def remove_cog(self, key: str) -> bool:
        data = await self.get_stored_cogs()
        if key not in data:
            return False
        del data[key]
        await self.config.stored_cogs.set(data)
        return True

    async def invoke_prefix(self, interaction: discord.Interaction, command_name: str, arguments: str = "") -> tuple[bool, str]:
        command = self.bot.get_command(command_name)
        if command is None:
            return False, f"Command nicht gefunden: {command_name}"

        context = await commands.Context.from_interaction(interaction)
        context.prefix = "°"
        context.command = command
        context.view = StringView(arguments)
        context.invoked_with = command_name.split(" ")[0]

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

    async def run(self, interaction: discord.Interaction, key: str) -> None:
        stored = await self.get_stored_cogs()
        selected = stored.get(key)
        if selected is None:
            await interaction.response.send_message(
                "Der ausgewählte Cog ist nicht mehr vorhanden.",
                ephemeral=True,
            )
            return

        if selected["cog_name"].strip().casefold() == "kuhmuhupdate":
            await interaction.response.send_message(
                "KuhmuhUpdate kann nicht über sich selbst aktualisiert werden.",
                ephemeral=True,
            )
            return

        if self.update_lock.locked():
            await interaction.response.send_message("⏭️ Ein Update läuft bereits.", ephemeral=True)
            return

        if not isinstance(interaction.channel, discord.TextChannel):
            await interaction.response.send_message("Bitte in einem Text-Channel ausführen.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        cog_name = selected["cog_name"]
        repo_name = selected["repo_name"]
        embed = discord.Embed(
            title=f"Update: {cog_name}",
            description=f"Repo: **{repo_name}**\n⏳ Update läuft …",
        )
        public_message = await interaction.channel.send(embed=embed)

        async with self.update_lock:
            results: list[StepResult] = []
            steps = [
                ("Uninstall", "cog uninstall", cog_name),
                ("Repo Update", "repo update", repo_name),
                ("Install", "cog install", f"{repo_name} {cog_name}"),
                ("Load", "load", cog_name),
            ]

            for name, command_name, arguments in steps:
                ok, output = await self.invoke_prefix(interaction, command_name, arguments)
                if name == "Uninstall" and not ok and self._not_installed(output):
                    results.append(StepResult(name, "⚠️", "Nicht installiert (weiter).", output))
                    continue

                results.append(
                    StepResult(
                        name,
                        "✅" if ok else "❌",
                        "Erfolgreich." if ok else "Fehler – Prozess beendet.",
                        output,
                    )
                )
                if not ok:
                    break

            await self._finalize(public_message, cog_name, repo_name, results)
            await interaction.followup.send("Update abgeschlossen.", ephemeral=True)

    async def _finalize(
        self,
        message: discord.Message,
        cog_name: str,
        repo_name: str,
        results: list[StepResult],
    ) -> None:
        limit = int(await self.config.embed_detail_limit() or 400)
        embed = discord.Embed(
            title=f"Update: {cog_name}",
            description=f"Repo: **{repo_name}**",
        )
        for result in results:
            detail = next((line.strip() for line in result.details.splitlines() if line.strip()), "")
            if len(detail) > limit:
                detail = detail[: max(0, limit - 1)] + "…"
            value = f"{result.status} {result.summary}"
            if detail:
                value += f"\n```text\n{detail}\n```"
            embed.add_field(name=result.name, value=value, inline=False)
        with contextlib.suppress(Exception):
            await message.edit(embed=embed)

    @staticmethod
    def _not_installed(text: str) -> bool:
        lowered = text.casefold()
        return any(value in lowered for value in ("not installed", "not found", "no such cog"))
