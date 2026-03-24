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

    def apply_search_state(self, search: Search) -> None:
        """
        Passt die Button-Zustände an den aktuellen Search-Status an.
        """
        is_open = search.is_open()

        self.join_button.disabled = not is_open
        self.leave_button.disabled = not is_open
        self.close_button.disabled = not is_open

        self.open_button.disabled = is_open
        self.delete_button.disabled = False

    @staticmethod
    def _extract_role_ids(interaction: discord.Interaction) -> tuple[int, ...]:
        """
        Extrahiert Rollen-IDs aus einem Interaction-User, sofern vorhanden.
        """
        roles = getattr(interaction.user, "roles", None)
        if not roles:
            return ()

        return tuple(role.id for role in roles)

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

        public_message_id = interaction.message.id if interaction.message else None

        result = await self._search_service.join_search(
            context=self._context,
            search_id=self._search_id,
            user_id=interaction.user.id,
            display_name=interaction.user.display_name,
        )

        await self._finalize_interaction(
            interaction,
            result,
            public_message_id=public_message_id,
        )

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

        public_message_id = interaction.message.id if interaction.message else None

        result = await self._search_service.leave_search(
            context=self._context,
            search_id=self._search_id,
            user_id=interaction.user.id,
        )

        await self._finalize_interaction(
            interaction,
            result,
            public_message_id=public_message_id,
        )

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

        public_message_id = interaction.message.id if interaction.message else None

        async def _confirm_close(confirm_interaction: discord.Interaction) -> None:
            result = await self._search_service.close_search(
                context=self._context,
                search_id=self._search_id,
                actor_user_id=confirm_interaction.user.id,
                actor_role_ids=self._extract_role_ids(confirm_interaction),
            )

            if result.changed:
                await self._refresh_public_message(
                    confirm_interaction,
                    result.search,
                    public_message_id=public_message_id,
                )

            await confirm_interaction.response.edit_message(
                content=result.user_message or "Suche geschlossen.",
                view=None,
            )

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

        public_message_id = interaction.message.id if interaction.message else None

        result = await self._search_service.open_search(
            context=self._context,
            search_id=self._search_id,
            actor_user_id=interaction.user.id,
            actor_role_ids=self._extract_role_ids(interaction),
        )

        await self._finalize_interaction(
            interaction,
            result,
            public_message_id=public_message_id,
        )

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

        public_message_id = interaction.message.id if interaction.message else None

        async def _confirm_delete(confirm_interaction: discord.Interaction) -> None:
            await confirm_interaction.response.edit_message(
                content="Suche wird gelöscht...",
                view=None,
            )

            result = await self._search_service.delete_search(
                context=self._context,
                search_id=self._search_id,
                actor_user_id=confirm_interaction.user.id,
                actor_role_ids=self._extract_role_ids(confirm_interaction),
            )

            if result.changed:
                await self._refresh_public_message(
                    confirm_interaction,
                    result.search,
                    public_message_id=public_message_id,
                )

            await confirm_interaction.edit_original_response(
                content=result.user_message or "Suche wurde gelöscht.",
                view=None,
            )

        confirm_view = ConfirmActionView(
            confirm_callback=_confirm_delete,
            confirm_label="Ja, endgültig löschen",
            cancel_label="Abbrechen",
        )

        await interaction.response.send_message(
            "Möchtest du diese Suche wirklich endgültig löschen?\n⚠️ Dieser Vorgang kann nicht rückgängig gemacht werden.",
            view=confirm_view,
            ephemeral=True,
        )

    async def _finalize_interaction(
        self,
        interaction: discord.Interaction,
        result,
        *,
        public_message_id: int | None,
    ) -> None:
        """
        Standardabschluss für direkte Aktionen ohne Confirm-Zwischenschritt.
        """
        if result.changed:
            await self._refresh_public_message(
                interaction,
                result.search,
                public_message_id=public_message_id,
            )

        await interaction.response.send_message(
            result.user_message or "Aktion abgeschlossen.",
            ephemeral=True,
        )

    async def _refresh_public_message(
        self,
        interaction: discord.Interaction,
        search: Search | None,
        *,
        public_message_id: int | None,
    ) -> None:
        """
        Aktualisiert die öffentliche Suchnachricht oder entfernt die View nach Löschung.
        """
        if public_message_id is None or interaction.channel is None:
            return

        try:
            public_message = await interaction.channel.fetch_message(public_message_id)
        except discord.NotFound:
            return

        if search is None:
            await public_message.edit(view=None)
            return

        render_data = self._search_renderer.render_search(search)
        embed = self._embed_builder(render_data)

        refreshed_view = PublicSearchView(
            context=self._context,
            search_id=self._search_id,
            search_service=self._search_service,
            search_renderer=self._search_renderer,
            embed_builder=self._embed_builder,
            timeout=self.timeout,
        )
        refreshed_view.apply_search_state(search)

        await public_message.edit(
            embed=embed,
            view=refreshed_view,
        )