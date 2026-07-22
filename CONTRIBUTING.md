# Mitwirken

Beiträge zu MediaHub-AI-Node sind willkommen.

## Grundablauf

1. Repository forken.
2. Einen eigenen Branch erstellen.
3. Änderungen klein und nachvollziehbar halten.
4. Tests ergänzen oder aktualisieren.
5. `python -m pytest` und `ruff check .` ausführen.
6. Pull Request mit Problem, Lösung und Testbeschreibung öffnen.

## Regeln

- Keine Passwörter, Tokens, privaten Pfade oder personenbezogenen Daten einreichen.
- Neue Abhängigkeiten müssen in `THIRD_PARTY_LICENSES.md` dokumentiert werden.
- Öffentliche APIs sollen rückwärtskompatibel bleiben oder eine klare Migration erhalten.
- Linux und Raspberry Pi bleiben primäre Zielplattformen.
- Funktionen müssen auch ohne Cloud-Anbieter sinnvoll nutzbar bleiben.

## Commit-Nachrichten

Beispiele:

```text
feat: add knowledge graph endpoint
fix: prevent duplicate relation imports
docs: expand Raspberry Pi restore guide
test: cover dry-run item imports
```
