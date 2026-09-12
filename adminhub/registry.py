from __future__ import annotations

from dataclasses import dataclass
from typing import Awaitable, Callable, Union

import discord


PanelPermissionCheck = Callable[[discord.Interaction], Union[bool, Awaitable[bool]]]
PanelEmbedBuilder = Callable[[discord.Interaction], Union[discord.Embed, Awaitable[discord.Embed]]]
PanelViewBuilder = Callable[[discord.Interaction], Union[discord.ui.View | None, Awaitable[discord.ui.View | None]]]


@dataclass(frozen=True)
class AdminPanel:
    """
    Beschreibt ein einzelnes Modul im Admin-Hub.

    Ein Panel wird von einem migrierten Cog registriert und liefert Titel,
    Kurzbeschreibung sowie eine Funktion zum Aufbau seines Embeds. Die
    fachliche Logik bleibt vollstaendig im migrierten Cog; der Hub ruft sie
    nur auf und stellt die gemeinsame Navigation bereit.
    """

    key: str
    label: str
    description: str
    build_embed: PanelEmbedBuilder
    build_view: PanelViewBuilder | None = None
    required_check: PanelPermissionCheck | None = None


class AdminPanelRegistry:
    """Verwaltet die im Admin-Hub verfuegbaren Panels."""

    def __init__(self) -> None:
        self._panels: dict[str, AdminPanel] = {}

    def register(self, panel: AdminPanel) -> None:
        self._panels[panel.key] = panel

    def unregister(self, key: str) -> None:
        self._panels.pop(key, None)

    def get(self, key: str) -> AdminPanel | None:
        return self._panels.get(key)

    def all(self) -> list[AdminPanel]:
        return sorted(self._panels.values(), key=lambda panel: panel.label.casefold())
