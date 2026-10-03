# KuhMuh V2 – Agent-Anweisungen

Verbindliche Regeln für KI-Agenten (Claude Code, GitHub Copilot) in diesem Repository.
Quelle: `V2 KUHMUH_RULEBOOK.md` (v1.12) und `V2 KUHMUH_WORKMODE.md`.

## Projekt

- Dieses Repo (`Lucarye/kuhmuh-core`) ist **V2**: Red-DiscordBot-Cogs (`adminhub`, `groupfinder`, `kuhmuhupdate_v2`, `logging`). Wo die Quell-Dokumente `V2/` schreiben, ist der Repo-Root gemeint.
- **V1** ist ein eigenständiges Repo (`Lucarye/kuhmuh-cogs`, lokal `../kuhmuh-cogs`). V1 und V2 nicht vermischen, V1-Dateien nie ändern.
- Das laufende Bot-System besteht aus mehreren Repos. Ein Cog gilt erst als entfernt, wenn Repo und Red-Ladezustand geklärt sind. Repo-Bestand, installierte Cogs, registrierte Commands und Runtime getrennt erfassen.
- Community-Cogs fallen nicht unter diese Regeln.
- Betrieb: serverintern, eigenverwaltet, keine externe Distribution, mit Admin-Rechten.
- Python 3.11, Red-DiscordBot 3.5.22, Umgebung über uv (`uv sync`).

## Systemwerte

```text
OWNER_ID          = 359447597427064833
ADMIN_ROLE_ID     = 1198650646786736240
OFFIZIER_ROLE_ID  = 1198652039312453723
GUILD_ID          = 1198649628787212458
BOT_KATEGORIE_ID  = 1460005712041349201
TEST_CHANNEL_ID   = 1199322485297000528
TEST_ROLE_ID      = 1445018518562017373
MUHKUH_EMOJI      = <:muhkuh:1207038544510586890>
```

## Arbeitsablauf

1. Anfrage und betroffenen Codepfad bestimmen.
2. Relevante Dateien, Symbole, Konfiguration und Abhängigkeiten lesen. Nichts über Dateien, Commands, Ladezustände oder Abhängigkeiten annehmen.
3. Lokale Hypothese formulieren und einen günstigen Gegencheck bestimmen.
4. Kleinste passende Änderung umsetzen.
5. Direkt validieren (siehe unten).
6. Nach erfolgreicher Validierung in `Änderungen.md` dokumentieren.

Bei unklarem oder widersprüchlichem Ist-Stand nicht raten: nächsten Codepfad prüfen oder die offene Frage benennen.

### Aussagen, Annahmen, Schätzungen

- Geprüfte Fakten, Zielvorgaben, Annahmen und offene Punkte sprachlich getrennt benennen.
- Unverifizierte Annahmen begründen keine Implementierungsentscheidung.
- Aufwand, Dauer, Reichweite nur mit Grundlage und Unsicherheitsbereich, gekennzeichnet als `Schätzung`.

### Pflichtabfrage bei neuen Cogs

Vor dem ersten Edit an einem neuen Cog fragen, ob er in den Admin-Hub soll. Antwort muss `Admin-Hub: Ja`, `Admin-Hub: Nein` oder eine bewusste Zurückstellung sein; vorher keine Implementierung.

- `Ja`: `ADMIN_HUB_ENABLED = True` plus `get_admin_panel()` (Referenz: `kuhmuhupdate_v2`).
- `Nein`: keine automatische Registrierung.
- Admin-Hub ist immer Opt-in. Member-facing Cogs (insbesondere die Gruppensuche) nicht allein wegen ihrer Existenz aufnehmen.
- Migration bestehender Cogs nur nach Review und Test, als neue V2-Logik.

## Änderungsregeln

- Änderungen fachlich und räumlich minimal. Keine unbeteiligten Refactorings, Formatierungswellen oder Architekturumbauten in einer Sachkorrektur.
- Bestehende Nutzeränderungen nicht ungefragt zurücksetzen.
- Öffentliche Commands und gespeicherte Datenformate nur mit bewerteter Kompatibilität ändern.
- Im vorhandenen Stil arbeiten. Kommentare nur für nicht offensichtliche Entscheidungen.
- Deutsche Umlaute und ß korrekt schreiben (`ä ö ü ß`), ASCII-Umschreibung nur wenn technisch zwingend.
- **Keine Commits oder Branches**, außer ausdrücklich beauftragt.

## Architektur

- Ein Cog hat eine erkennbare fachliche Verantwortung; neue Funktionen nicht in fachfremde Cogs.
- Konfiguration, Berechtigungen, UI, Persistenz und Hintergrundtasks trennen, soweit der Bestand es sinnvoll zulässt.
- Guild-spezifische Werte nur wenn fachlich nötig. Rollen-, Channel-, Guild- und Repo-Abhängigkeiten im Code oder in der Doku eindeutig erkennbar machen.
- Berechtigungsprüfungen (Owner, Admin, Rolle, `manage_guild`) im jeweiligen Cog nachvollziehbar. Massenänderungen brauchen bewusste Freigabe.
- Automatisierung ersetzt keine Berechtigungsprüfung. Hintergrundtasks brauchen nachvollziehbares Start-, Stop- und Fehlerhandling; Retries, Locks, Cooldowns begründet und begrenzt.
- `logging` ist Referenz-Cog für neue Arbeiten (V1-Referenz: `willkommen`), aber kein Beleg für eine einheitliche Struktur.

### Slash-Commands

- Commands nur per Decorator am Cog (`@app_commands.guilds(...)` + `@app_commands.command(...)`): Guild-scoped, Berechtigungs- und Guild-Prüfung, stabile Beschreibung und eindeutige Optionen.
- **Verboten in Cogs:** `bot.tree.sync()`, `clear_commands()`, `copy_global_to()`, manuelles `add_command()`/`remove_command()` – auch nicht in `cog_load()`, `cog_unload()` oder Startup-Tasks. Ein Guild-Sync überschreibt die komplette Command-Liste; fehlt ein Command im lokalen Tree, wird er gelöscht und mit neuer ID neu angelegt, die Berechtigungen aus den Server-Integrationen gehen verloren.
- Sync nur manuell per `[p]slash sync <GUILD_ID>`, wenn sich Command-Definitionen geändert haben und alle Cogs geladen sind.
- Name und Typ eines Commands sind stabil. Umbenennen/Entfernen löscht Berechtigungen dauerhaft und muss in `Änderungen.md` vermerkt werden.

### Ausgaben und Logging

- Ausgaben klar, knapp, administrierbar. Status-Icons `✅ ⚠️ ❌ ⏭️`; `MUHKUH_EMOJI` als primäres Projekt-Emoji, wo passend.
- Nutzerantworten, Konsolenlogs und Discord-Logchannel-Embeds sind getrennte Pfade.
- Logs verwertbar, ohne unnötige Wiederholungen. Vor Logging-Änderungen Zielchannel, Logkategorie und Berechtigung prüfen.

## Validierung

Jede Codeänderung braucht mindestens einen Nachweis, in dieser Reihenfolge:

1. Verhaltenstest oder gezielter Test.
2. Sonst Syntax-, Type-, Lint- oder enger Importcheck:
   - `uv run ruff check <pfad>`
   - `uv run ruff format --check <pfad>`
   - `uv run pyrefly check`
3. Sonst gezielte Inhaltsprüfung mit benannter Restunsicherheit.

Schlägt ein Check fehl: im betroffenen Codepfad bleiben, Ursache beheben, denselben Check wiederholen, erst dann erweitern.

## Dokumentation

- `Analyse.md`: geprüfter Ist-Stand, Runtime-Beobachtungen, Doppelungen, offene Architekturentscheidungen.
- `Änderungen.md`: chronologisches technisches Protokoll.
  - Datum/Uhrzeit **unmittelbar vor jedem Eintrag** per eigener Systemzeit-Abfrage ermitteln (z. B. `date "+%d.%m.%Y, %H:%M:%S %:z"`), Zeitzone mitführen. Keine Chat-, Editor- oder Dateizeit.
  - Nur validierte Änderungen als `AKTIV` eintragen.
  - Einträge ergänzen, nie löschen oder still überschreiben; bei Anpassung/Rücknahme Status setzen und auf Folgeeintrag verweisen.
- `Patchnotes.md`: nur veröffentlichte, kompakte Zusammenfassungen abgeschlossener Änderungen; nicht automatisch pflegen.

## Ergebnisbericht

Am Ende jeder Arbeit kurz nennen: was geändert wurde, welche Dateien/Commands betroffen sind, wie validiert wurde, welche Risiken oder offenen Entscheidungen bleiben.
