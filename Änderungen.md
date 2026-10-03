# Änderungen V2

> Diese Datei protokolliert ausschließlich technische Änderungen am V2-Repositoryteil (`V2/`). Änderungen am V1-Teil gehören nicht hierher, sondern in [`../V1/Änderungen.md`](../V1/Änderungen.md).

Der gemeinsame Verlauf vor der Repo-Trennung steht weiterhin im Archiv unter [`../Änderungen.md`](../Änderungen.md), unter anderem die Historie zu `V2/adminhub` und `V2/kuhmuhupdate_v2` bis 12.09.2026, 23:39:25 Uhr.

## 27.09.2026, 21:31:01 +02:00

- AKTIV: V1 und V2 als eigenständige Repositories dokumentiert. `Analyse.md`, `Änderungen.md` und `Patchnotes.md` für V2 unter `V2/` neu angelegt.
- Die bisherigen Root-Dateien `Analyse.md`, `Änderungen.md` und `Patchnotes.md` gelten ab sofort als eingefrorenes Archiv des gemeinsamen Standes vor der Trennung und werden nicht weiter fortgeschrieben.
- `V2 KUHMUH_RULEBOOK.md` und `V2 KUHMUH_WORKMODE.md` wurden entsprechend auf die lokalen V2-Dokumente umgestellt.
- Validierung: Inhaltsprüfung der neu angelegten und geänderten Dokumente; keine Codeänderung.

## 03.10.2026, 15:36:10 +02:00

- AKTIV: `pyproject.toml` angelegt. Projekt auf uv umgestellt (`requires-python ==3.11.*`, `Red-DiscordBot==3.5.22`, Dev-Gruppe `ruff`, `pyrefly`), `uv.lock` erzeugt, `requirements.txt` entfernt.
- AKTIV: Ruff-Konfiguration (py311, Zeilenlänge 100, Regeln E/W/F/I/B/UP/ASYNC/SIM/RUF) und Pyrefly-Konfiguration ergänzt. Keine Codeänderung; Befunde (75 Ruff, 40 Pyrefly) noch offen.
- AKTIV: `AGENTS.md` (gelesen von GitHub Copilot) und `CLAUDE.md` (importiert `AGENTS.md`, gelesen von Claude Code) aus `V2 KUHMUH_RULEBOOK.md` und `V2 KUHMUH_WORKMODE.md` abgeleitet. Die Quelldokumente bleiben unverändert bestehen.
- Validierung: `uv lock`, `uv sync`, `uv run ruff check --no-cache .` und `uv run pyrefly check` laufen; Inhaltsprüfung von `AGENTS.md` gegen die Quelldokumente.
