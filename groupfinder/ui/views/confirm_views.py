from __future__ import annotations

from collections.abc import Awaitable, Callable

import discord


ConfirmCallback = Callable[[discord.Interaction], Awaitable[None]]


class ConfirmActionView(discord.ui.View):
    """
    Einfache Bestätigungs-View für sensible Aktionen.

    Die View selbst enthält keine Fachlogik. Sie führt bei Bestätigung
    lediglich den übergebenen Callback aus.
    """

    def __init__(
        self,
        *,
        confirm_callback: ConfirmCallback,
        confirm_label: str = "Bestätigen",
        cancel_label: str = "Abbrechen",
        timeout: float | None = 60,
    ) -> None:
        super().__init__(timeout=timeout)
        self._confirm_callback = confirm_callback
        self._confirm_label = confirm_label
        self._cancel_label = cancel_label

        self._apply_labels()

    def _apply_labels(self) -> None:
        self.confirm_button.label = self._confirm_label
        self.cancel_button.label = self._cancel_label

    @discord.ui.button(label="Bestätigen", style=discord.ButtonStyle.danger, row=0)
    async def confirm_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        del button

        await self._confirm_callback(interaction)
        self.stop()

    @discord.ui.button(label="Abbrechen", style=discord.ButtonStyle.secondary, row=0)
    async def cancel_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        del button

        await interaction.response.send_message(
            "Aktion abgebrochen.",
            ephemeral=True,
        )
        self.stop()