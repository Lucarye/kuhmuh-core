from __future__ import annotations

import discord
from discord import app_commands
from redbot.core import commands

from adminhub.registry import AdminAction, AdminCommandInfo, AdminPanel
from .service import KuhmuhUpdateService


GUILD_ID = 1198649628787212458
OWNER_ID = 359447597427064833
ADMIN_ROLE_ID = 1198650646786736240
OFFIZIER_ROLE_ID = 1198652039312453723


class AddCogModal(discord.ui.Modal, title="Cog speichern"):
    cog_name = discord.ui.TextInput(label="Cog-Name", max_length=100)
    repo_name = discord.ui.TextInput(label="Repository-Name", max_length=100)

    def __init__(self, cog: "KuhmuhUpdateV2") -> None:
        super().__init__()
        self.cog = cog

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await self.cog.service.add_cog(self.cog_name.value, self.repo_name.value)
        await interaction.response.send_message(
            f"✅ Gespeichert: **{self.cog_name.value.strip()}** → `{self.repo_name.value.strip()}`",
            ephemeral=True,
        )


class StoredCogSelect(discord.ui.Select):
    def __init__(self, cog: "KuhmuhUpdateV2", operation: str) -> None:
        self.cog = cog
        self.operation = operation
        options = [
            discord.SelectOption(
                label=f"{value['cog_name']} ({value['repo_name']})"[:100],
                value=key,
            )
            for key, value in cog.stored_cogs_cache.items()
        ][:25]
        super().__init__(
            placeholder="Gespeicherten Cog auswählen …",
            options=options or [discord.SelectOption(label="Keine Cogs gespeichert", value="__none__")],
            disabled=not options,
            min_values=1,
            max_values=1,
            custom_id=f"kuhmuhupdate_v2_select:{operation}",
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        key = self.values[0]
        if key == "__none__":
            await interaction.response.send_message("Keine gespeicherten Cogs vorhanden.", ephemeral=True)
            return

        if self.operation == "run":
            await self.cog.service.run(interaction, key)
            return

        removed = await self.cog.service.remove_cog(key)
        await interaction.response.send_message(
            "✅ Eintrag entfernt." if removed else "⚠️ Eintrag nicht gefunden.",
            ephemeral=True,
        )


class StoredCogSelectView(discord.ui.View):
    def __init__(self, cog: "KuhmuhUpdateV2", operation: str) -> None:
        super().__init__(timeout=180)
        self.add_item(StoredCogSelect(cog, operation))


class KuhmuhUpdateV2(commands.Cog):
    """KuhmuhUpdate als V2-Panel ohne eigene Discord-Commands."""

    ADMIN_HUB_ENABLED = True

    def __init__(self, bot) -> None:
        self.bot = bot
        self.service = KuhmuhUpdateService(bot)
        self.admin_hub = None
        self.stored_cogs_cache: dict[str, dict[str, str]] = {}

    async def refresh_cache(self) -> None:
        self.stored_cogs_cache = await self.service.get_stored_cogs()

    def is_authorized(self, interaction: discord.Interaction) -> bool:
        user = interaction.user
        if user.id == OWNER_ID:
            return True
        role_ids = {role.id for role in getattr(user, "roles", ())}
        return bool(role_ids & {ADMIN_ROLE_ID, OFFIZIER_ROLE_ID})

    async def build_embed(self, _interaction: discord.Interaction) -> discord.Embed:
        await self.refresh_cache()
        embed = discord.Embed(
            title="KuhmuhUpdate V2",
            description="Cogs aktualisieren und verwalten.",
            color=discord.Color.orange(),
        )
        if not self.stored_cogs_cache:
            embed.add_field(name="Gespeicherte Cogs", value="Keine Einträge vorhanden.", inline=False)
        else:
            lines = [
                f"• **{value['cog_name']}** → `{value['repo_name']}`"
                for _, value in sorted(
                    self.stored_cogs_cache.items(),
                    key=lambda item: item[1]["cog_name"].casefold(),
                )
            ]
            embed.add_field(name="Gespeicherte Cogs", value="\n".join(lines)[:1024], inline=False)
        embed.add_field(
            name="Ablauf",
            value="Repository aktualisieren, Cog installieren und anschließend laden.",
            inline=False,
        )
        return embed

    async def open_run(self, interaction: discord.Interaction) -> None:
        await self.refresh_cache()
        await interaction.response.send_message(
            "Wähle den Cog für `run` aus.",
            view=StoredCogSelectView(self, "run"),
            ephemeral=True,
        )

    async def open_remove(self, interaction: discord.Interaction) -> None:
        await self.refresh_cache()
        await interaction.response.send_message(
            "Wähle den zu entfernenden Eintrag aus.",
            view=StoredCogSelectView(self, "remove"),
            ephemeral=True,
        )

    async def open_add(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_modal(AddCogModal(self))

    async def refresh_panel(self, interaction: discord.Interaction) -> None:
        if self.admin_hub is None:
            await interaction.response.send_message("Admin-Hub ist nicht verfügbar.", ephemeral=True)
            return
        await interaction.response.edit_message(
            embed=await self.build_embed(interaction),
            view=self.admin_hub.build_panel_view("kuhmuhupdate_v2"),
        )

    def get_admin_panel(self) -> AdminPanel:
        return AdminPanel(
            key="kuhmuhupdate_v2",
            label="KuhmuhUpdate V2",
            description="Cogs nach Repository-Änderungen aktualisieren.",
            build_embed=self.build_embed,
            commands=(
                AdminCommandInfo(
                    name="run",
                    description="Führt Uninstall, Repository-Update, Install und Load aus.",
                    usage="Cog auswählen → Run",
                ),
                AdminCommandInfo(
                    name="manage add",
                    description="Speichert eine Cog-/Repository-Zuordnung.",
                    usage="Hinzufügen",
                ),
                AdminCommandInfo(
                    name="manage remove",
                    description="Entfernt eine gespeicherte Zuordnung.",
                    usage="Entfernen",
                ),
                AdminCommandInfo(
                    name="manage list",
                    description="Zeigt gespeicherte Zuordnungen.",
                    usage="Aktualisieren",
                ),
            ),
            actions=(
                AdminAction(
                    key="run",
                    label="Run",
                    description="Update-Ablauf starten",
                    callback=self.open_run,
                    required_check=self.is_authorized,
                ),
                AdminAction(
                    key="add",
                    label="Hinzufügen",
                    description="Cog speichern",
                    callback=self.open_add,
                    required_check=self.is_authorized,
                ),
                AdminAction(
                    key="remove",
                    label="Entfernen",
                    description="Cog-Zuordnung entfernen",
                    callback=self.open_remove,
                    required_check=self.is_authorized,
                ),
                AdminAction(
                    key="refresh",
                    label="Aktualisieren",
                    description="Liste neu laden",
                    callback=self.refresh_panel,
                    required_check=self.is_authorized,
                ),
            ),
            required_check=self.is_authorized,
        )

    async def cog_load(self) -> None:
        admin_hub = self.bot.get_cog("AdminHubCog")
        if admin_hub is not None and self.ADMIN_HUB_ENABLED:
            self.admin_hub = admin_hub
            admin_hub.register_panel(self.get_admin_panel())
