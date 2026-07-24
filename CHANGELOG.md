# Changelog

Alle wesentlichen Änderungen an MediaHub-AI-Node werden in dieser Datei dokumentiert.

## [Unreleased]

### Hinzugefügt

- öffentliche Repository-Struktur
- MIT-Lizenz
- vollständige Dokumentationsstruktur
- GitHub-Actions für Tests, Release und Dokumentation
- Backup-, Restore- und Wartungsdokumentation
- `health_check.sh`
- Sicherheits- und Beitragsrichtlinien

## [0.7.1] - 2026-07-24

### Geändert

- Release-Paketbau korrigiert.
- GitHub-Releases erhalten vollständige Release-Beschreibungen.
- Installation über Release-ZIP und direkte Git-Installation dokumentiert.
- Versionsangaben vereinheitlicht.
- Gemeinsamen MediaHub-Repository-Standard ergänzt.
- Temporäre Release-Notizen werden nach erfolgreichem Release entfernt.

## [0.1.0] - 2026-07-22

### Funktionsfähiger Raspberry-Pi-Teststand

- systemd-Dienst
- REST-API auf Port 8765
- Health-Endpunkt
- Wissensdatenbank
- Titel-, Alias- und externe-ID-Erkennung
- Dublettenerkennung
- Merge-Service
- Importer
- Beziehungsimport
- Graphprüfung
- Backup- und Restore-Skripte
- automatischer Abschlusstest mit 5 von 5 bestandenen Prüfungen
