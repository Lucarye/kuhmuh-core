# Analyse V2

Stand: 2026-09-27

## 1. Geltungsbereich

Diese Datei dokumentiert ausschließlich den Ist-Stand des V2-Repositoryteils (`V2/`). V1 wird hier nicht mitgeführt; der V1-Ist-Stand steht in [`../V1/Analyse.md`](../V1/Analyse.md).

Der gemeinsame Stand vor der Repo-Trennung (27.09.2026) steht weiterhin im Archiv unter [`../Analyse.md`](../Analyse.md). Dort dokumentierte V2-Cogs, Architekturentscheidungen und offene Punkte (u. a. `V2/groupfinder`, `V2/logging`, `V2/adminhub`, `V2/kuhmuhupdate_v2`) gelten bis zum Trennungszeitpunkt unverändert fort und werden hier nicht erneut kopiert.

## 2. Fortführung

Ab dem Trennungszeitpunkt werden neue V2-spezifische Analyseergebnisse, Abweichungen und offene Entscheidungen ausschließlich hier ergänzt. Bestehende Einträge werden nicht gelöscht oder stillschweigend überschrieben.

## 3. Offene Punkte (übernommen aus dem Archiv)

- `V2/groupfinder` ist als MVP gekennzeichnet und noch keine vollständige Funktionsparität zu V1.
- `V2/main.py`, `V2/README.md` und `V2/requirements.txt` sind bislang leer.
- `V2/adminhub` benötigt für jede Aufnahme eines Cogs weiterhin das ausdrückliche Opt-in `ADMIN_HUB_ENABLED = True`.
