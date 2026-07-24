# Mitwirken

## Vorbereitung

- Änderungen in einem eigenen Branch durchführen
- verständliche Commit-Nachrichten verwenden
- bestehende Struktur und Formatierung beibehalten
- keine Geheimnisse, Tokens oder privaten Daten einchecken

## Vor einem Commit

```bash
python -m pytest
python -m ruff check .
```

## Pull Requests

Ein Pull Request sollte enthalten:

- Zweck der Änderung
- betroffene Komponenten
- durchgeführte Tests
- mögliche Risiken oder Migrationen
- Aktualisierung der Dokumentation bei geändertem Verhalten

Größere Architekturänderungen sollten vor der Umsetzung abgestimmt werden.
