from __future__ import annotations

from collections.abc import Callable

import discord

from ...core.models.context import Context
from ...core.models.search import Search
from ...core.services.search_service import SearchService
from ..renderers.search_renderer import SearchRenderer
from .confirm_views import ConfirmActionView


class PublicSearchView(discord.ui.View):
    """
    Öffentliche View für eine aktive Gruppensuche.

    Diese View sammelt UI-Interaktionen ein, reicht sie an den SearchService
    weiter und aktualisiert bei erfolgreichen Änderungen die öffentliche Nachricht.
    """

    def __init__(
        self,
        *,
        context: Context,
        search_id: str,
        search_service: SearchService,
        search_renderer: SearchRenderer,
        embed_builder: Callable[[dict], discord.Embed],
        timeout: float | None = None,
    ) -> None:
        super().__init__(timeout=timeout)
        self._context = context
        self._search_id = search_id
        self._search_service = search_service
        self._search_renderer = search_renderer
        self._embed_builder = embed_builder

    @discord.ui.button(label="Beitreten", style=discord.ButtonStyle.success, row=0)
    async def join_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        del button

        if interaction.user is None:
            await interaction.response.send_message(
                "Die Aktion konnte nicht ausgeführt werden.",
                ephemeral=True,
            )
            return

        result = await self._search_service.join_search(
            context=self._context,
            search_id=self._search_id,
            user_id=interaction.user.id,
            display_name=interaction.user.display_name,
        )

        await self._finalize_interaction(interaction, result)

    @discord.ui.button(label="Verlassen", style=discord.ButtonStyle.secondary, row=0)
    async def leave_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        del button

        if interaction.user is None:
            await interaction.response.send_message(
                "Die Aktion konnte nicht ausgeführt werden.",
                ephemeral=True,
            )
            return

        result = await self._search_service.leave_search(
            context=self._context,
            search_id=self._search_id,
            user_id=interaction.user.id,
        )

        await self._finalize_interaction(interaction, result)

    @discord.ui.button(label="Schließen", style=discord.ButtonStyle.danger, row=1)
    async def close_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        del button

        if interaction.user is None:
            await interaction.response.send_message(
                "Die Aktion konnte nicht ausgeführt werden.",
                ephemeral=True,
            )
            return

        async def _confirm_close(confirm_interaction: discord.Interaction) -> None:
            result = await self._search_service.close_search(
                context=self._context,
                search_id=self._search_id,
                actor_user_id=confirm_interaction.user.id,
            )
            await self._finalize_interaction(confirm_interaction, result)

        confirm_view = ConfirmActionView(
            confirm_callback=_confirm_close,
            confirm_label="Schließen bestätigen",
            cancel_label="Abbrechen",
        )

        await interaction.response.send_message(
            "Möchtest du diese Gruppensuche wirklich schließen?",
            view=confirm_view,
            ephemeral=True,
        )

    @discord.ui.button(label="Öffnen", style=discord.ButtonStyle.primary, row=1)
    async def open_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        del button

        if interaction.user is None:
            await interaction.response.send_message(
                "Die Aktion konnte nicht ausgeführt werden.",
                ephemeral=True,
            )
            return

        result = await self._search_service.open_search(
            context=self._context,
            search_id=self._search_id,
            actor_user_id=interaction.user.id,
        )

        await self._finalize_interaction(interaction, result)

    @discord.ui.button(label="Löschen", style=discord.ButtonStyle.danger, row=1)
    async def delete_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        del button

        if interaction.user is None:
            await interaction.response.send_message(
                "Die Aktion konnte nicht ausgeführt werden.",
                ephemeral=True,
            )
            return

        async def _confirm_delete(confirm_interaction: discord.Interaction) -> None:
            result = await self._search_service.delete_search(
                context=self._context,
                search_id=self._search_id,
                actor_user_id=confirm_interaction.user.id,
            )
            await self._finalize_interaction(confirm_interaction, result)

        confirm_view = ConfirmActionView(
            confirm_callback=_confirm_delete,
            confirm_label="Löschen bestätigen",
            cancel_label="Abbrechen",
        )

        await interaction.response.send_message(
            "Möchtest du diese Gruppensuche wirklich löschen?",
            view=confirm_view,
            ephemeral=True,
        )

    async def _finalize_interaction(self, interaction: discord.Interaction, result) -> None:
        """
        Sendet die ephemere Rückmeldung und aktualisiert bei Bedarf die öffentliche Nachricht.
        """
        if result.changed:
            await self._refresh_public_message(interaction, result.search)

        await interaction.response.send_message(
            result.user_message or "Aktion abgeschlossen.",
            ephemeral=True,
        )

    async def _refresh_public_message(
        self,
        interaction: discord.Interaction,
        search: Search | None,
    ) -> None:
        """
        Aktualisiert die öffentliche Suchnachricht oder entfernt die View nach Löschung.
        """
        if interaction.message is None:
            return

        if search is None:
            await interaction.message.edit(view=None)
            return

        render_data = self._search_renderer.render_search(search)
        embed = self._embed_builder(render_data)

        await interaction.message.edit(
            embed=embed,
            view=self,
        )