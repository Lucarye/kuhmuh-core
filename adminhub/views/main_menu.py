from __future__ import annotations

import discord

from ..registry import AdminAction, AdminPanel


async def _build_panel_embed(panel: AdminPanel, interaction: discord.Interaction) -> discord.Embed:
    embed = panel.build_embed(interaction)
    if hasattr(embed, "__await__"):
        embed = await embed  # type: ignore[assignment]

    if panel.commands:
        lines = []
        for command in panel.commands:
            usage = f" — `{command.usage}`" if command.usage else ""
            lines.append(f"**{command.name}**{usage}\n{command.description}")
        embed.add_field(name="Funktionen", value="\n\n".join(lines)[:1024], inline=False)

    return embed


class AdminPanelView(discord.ui.View):
    """Cog-Seite mit Aktionen und verpflichtender Rücknavigation."""

    def __init__(self, cog, panel: AdminPanel) -> None:
        super().__init__(timeout=None)
        self.cog = cog
        self.panel = panel

        for action in panel.actions:
            button = discord.ui.Button(
                label=action.label[:80],
                style=discord.ButtonStyle.primary,
                custom_id=f"kuhmuh_adminhub_action:{panel.key}:{action.key}",
            )
            button.callback = self._make_action_callback(action)
            self.add_item(button)

        back_button = discord.ui.Button(
            label="Hauptmenü",
            style=discord.ButtonStyle.secondary,
            custom_id=f"kuhmuh_adminhub_back:{panel.key}",
            row=4,
        )
        back_button.callback = self._go_to_main_menu
        self.add_item(back_button)

    def _make_action_callback(self, action: AdminAction):
        async def callback(interaction: discord.Interaction) -> None:
            if not self.cog.is_authorized(interaction.user):
                await interaction.response.send_message(
                    "Dafür fehlen dir die erforderlichen Berechtigungen.",
                    ephemeral=True,
                )
                return

            if action.required_check is not None:
                allowed = action.required_check(interaction)
                if hasattr(allowed, "__await__"):
                    allowed = await allowed
                if not allowed:
                    await interaction.response.send_message(
                        "Dafür fehlen dir die erforderlichen Berechtigungen.",
                        ephemeral=True,
                    )
                    return

            await action.callback(interaction)

        return callback

    async def _go_to_main_menu(self, interaction: discord.Interaction) -> None:
        await interaction.response.edit_message(
            embed=self.cog.build_main_embed(),
            view=AdminHubView(self.cog),
        )


class AdminHubButton(discord.ui.Button):
    """Button zum Öffnen einer registrierten Cog-Seite."""

    def __init__(self, cog, panel: AdminPanel, row: int) -> None:
        self.cog = cog
        super().__init__(
            label=panel.label[:80],
            style=discord.ButtonStyle.primary,
            custom_id=f"kuhmuh_adminhub_panel:{panel.key}",
            row=row,
        )
        self.panel = panel

    async def callback(self, interaction: discord.Interaction) -> None:
        panel = self.cog.registry.get(self.panel.key)
        if panel is None:
            await interaction.response.send_message("Dieses Modul ist nicht mehr verfügbar.", ephemeral=True)
            return
        await interaction.response.edit_message(
            embed=await _build_panel_embed(panel, interaction),
            view=AdminPanelView(self.cog, panel),
        )


class AdminHubView(discord.ui.View):
    """Persistente Hauptansicht des Admin-Hubs."""

    def __init__(self, cog) -> None:
        super().__init__(timeout=None)
        self.cog = cog
        panels = cog.registry.all()
        for index, panel in enumerate(panels):
            self.add_item(AdminHubButton(cog, panel, row=index // 5))
