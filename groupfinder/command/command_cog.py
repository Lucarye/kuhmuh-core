from __future__ import annotations

import discord
from redbot.core import app_commands, commands

from ..config.live import LIVE_CONTEXT
from ..config.shared import DEFAULT_INTERACTION_GUARD_SECONDS
from ..config.test import TEST_CONTEXT
from ..core.repository.search_repository import SearchRepository
from ..core.repository.session_repository import SessionRepository
from ..core.routing.context_router import ContextRouter
from ..core.services.dispatch_service import DispatchService
from ..core.services.interaction_guard_service import InteractionGuardService
from ..core.services.lock_service import LockService
from ..core.services.logging_service import LoggingService
from ..core.services.search_service import SearchService
from ..core.services.session_service import SessionService
from ..modules.groupfinder.module import GroupFinderModule
from ..ui.renderers.search_renderer import SearchRenderer
from ..ui.views.public_views import PublicSearchView


GUILD_ID = LIVE_CONTEXT.guild_id


class GroupFinderCommandCog(commands.Cog):
    """
    Zentraler Einstiegspunkt für Groupfinder.

    Der Cog übernimmt nur Orchestrierung:
    - Context bestimmen
    - Modul ansprechen
    - Core-Service aufrufen
    - Ergebnis in Discord ausgeben
    """

    def __init__(self, bot) -> None:
        self.bot = bot

        self.logging_service = LoggingService()
        self.search_repository = SearchRepository()
        self.session_repository = SessionRepository()
        self.lock_service = LockService()
        self.interaction_guard_service = InteractionGuardService(
            window_seconds=DEFAULT_INTERACTION_GUARD_SECONDS
        )
        self.dispatch_service = DispatchService(self.logging_service)
        self.session_service = SessionService(self.session_repository)
        self.search_service = SearchService(
            search_repository=self.search_repository,
            lock_service=self.lock_service,
            interaction_guard_service=self.interaction_guard_service,
            logging_service=self.logging_service,
            dispatch_service=self.dispatch_service,
        )

        self.groupfinder_module = GroupFinderModule()
        self.search_renderer = SearchRenderer(self.groupfinder_module)

        self.context_router = ContextRouter(
            contexts=[
                LIVE_CONTEXT,
                TEST_CONTEXT,
            ]
        )

    @app_commands.guilds(discord.Object(id=GUILD_ID))
    @app_commands.command(name="gruppensuche_v2", description="Erstellt eine neue Gruppensuche (V2).")
    @app_commands.describe(
        content_key="Der Content-Typ der Suche.",
        slots="Anzahl der Gruppenplätze.",
        title="Kurzer Titel oder Name der Suche.",
    )
    @app_commands.autocomplete(content_key="autocomplete_content_key")
    async def gruppensuche_command(
        self,
        interaction: discord.Interaction,
        content_key: str,
        slots: int,
        title: str,
    ) -> None:
        """
        Minimaler MVP-Einstieg zur Search-Erstellung.

        Später wird dieser Einstieg durch einen echten Create-Flow ergänzt.
        """
        if interaction.guild is None or interaction.channel is None or interaction.user is None:
            await interaction.response.send_message(
                "Die Gruppensuche kann hier nicht erstellt werden.",
                ephemeral=True,
            )
            return

        role_ids = []
        if hasattr(interaction.user, "roles"):
            role_ids = [role.id for role in interaction.user.roles]

        category_id = getattr(
            getattr(interaction.channel, "category", None), "id", None)

        context = self.context_router.resolve(
            guild_id=interaction.guild.id,
            channel_id=interaction.channel.id,
            category_id=category_id,
            role_ids=role_ids,
        )

        if context is None:
            await interaction.response.send_message(
                "Für diesen Channel oder deine Rollen konnte kein gültiger Kontext ermittelt werden.",
                ephemeral=True,
            )
            return

        validation_result = self.groupfinder_module.validate_create_payload(
            content_key=content_key,
            payload={"title": title, "description": ""},
            slots_total=slots,
        )

        if not validation_result.valid:
            await interaction.response.send_message(
                "\n".join(validation_result.errors),
                ephemeral=True,
            )
            return

        result = self.search_service.create_search(
            context=context,
            module_key=self.groupfinder_module.module_key,
            content_key=content_key,
            guild_id=interaction.guild.id,
            channel_id=interaction.channel.id,
            creator_id=interaction.user.id,
            slots_total=slots,
            payload=validation_result.normalized_payload,
        )

        if not result.success or result.search is None:
            await interaction.response.send_message(
                result.user_message or "Die Gruppensuche konnte nicht erstellt werden.",
                ephemeral=True,
            )
            return

        render_data = self.search_renderer.render_search(result.search)
        embed = self._build_embed(render_data)

        view = PublicSearchView(
            context=context,
            search_id=result.search.search_id,
            search_service=self.search_service,
            search_renderer=self.search_renderer,
            embed_builder=self._build_embed,
            timeout=None,
        )

        await interaction.response.send_message(
            embed=embed,
            view=view,
        )

    async def autocomplete_content_key(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> list[app_commands.Choice[str]]:
        """
        Liefert verfügbare Content-Keys als Autocomplete für den Slash-Command.
        """
        del interaction

        current_lower = current.lower().strip()
        choices: list[app_commands.Choice[str]] = []

        for definition in self.groupfinder_module.list_content_definitions():
            searchable = f"{definition.content_key} {definition.display_name}".lower()

            if current_lower and current_lower not in searchable:
                continue

            choices.append(
                app_commands.Choice(
                    name=f"{definition.display_name} ({definition.content_key})",
                    value=definition.content_key,
                )
            )

        return choices[:25]

    def _build_embed(self, render_data: dict) -> discord.Embed:
        """
        Baut für den MVP ein einfaches Discord-Embed aus den Render-Daten.
        """
        embed = discord.Embed(
            title=render_data["title"],
            description=render_data["subtitle"] or None,
        )

        if render_data["lines"]:
            embed.add_field(
                name="Details",
                value="\n".join(render_data["lines"]),
                inline=False,
            )

        participant_text = (
            "\n".join(render_data["participants"])
            if render_data["participants"]
            else "Noch keine Teilnehmer"
        )
        embed.add_field(
            name=f"Teilnehmer ({render_data['participant_count']}/{render_data['slots_total']})",
            value=participant_text,
            inline=False,
        )

        if render_data["waitlist"]:
            embed.add_field(
                name=f"Warteliste ({render_data['waitlist_count']})",
                value="\n".join(render_data["waitlist"]),
                inline=False,
            )

        embed.add_field(
            name="Status",
            value=render_data["status"],
            inline=False,
        )

        embed.set_footer(text=f"Search-ID: {render_data['search_id']}")
        return embed
