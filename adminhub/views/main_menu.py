from __future__ import annotations

import discord


class AdminHubSelect(discord.ui.Select):
    """Auswahl-Menue fuer die im Hub registrierten Module."""

    def __init__(self, cog) -> None:
        self.cog = cog
        panels = cog.registry.all()

        options = [
            discord.SelectOption(
                label=panel.label,
                value=panel.key,
                description=panel.description[:100] or None,
            )
            for panel in panels
        ] or [
            discord.SelectOption(label="Noch keine Module verfuegbar", value="__none__"),
        ]

        super().__init__(
            placeholder="Modul auswaehlen …",
            options=options,
            min_values=1,
            max_values=1,
            disabled=not panels,
            custom_id="kuhmuh_adminhub_select",
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        if not self.cog.is_authorized(interaction.user):
            await interaction.response.send_message(
                "Dafuer fehlen dir die erforderlichen Berechtigungen.",
                ephemeral=True,
            )
            return

        panel = self.cog.registry.get(self.values[0])
        if panel is None:
            await interaction.response.send_message(
                "Dieses Modul ist nicht mehr verfuegbar.",
                ephemeral=True,
            )
            return

        if panel.required_check is not None:
            allowed = panel.required_check(interaction)
            if hasattr(allowed, "__await__"):
                allowed = await allowed
            if not allowed:
                await interaction.response.send_message(
                    "Dafür fehlen dir die erforderlichen Berechtigungen.",
                    ephemeral=True,
                )
                return

        embed = panel.build_embed(interaction)
        if hasattr(embed, "__await__"):
            embed = await embed  # type: ignore[assignment]

        view = None
        if panel.build_view is not None:
            view = panel.build_view(interaction)
            if hasattr(view, "__await__"):
                view = await view

        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class AdminHubView(discord.ui.View):
    """Persistente Hauptansicht des Admin-Hubs."""

    def __init__(self, cog) -> None:
        super().__init__(timeout=None)
        self.cog = cog
        self.add_item(AdminHubSelect(cog))
