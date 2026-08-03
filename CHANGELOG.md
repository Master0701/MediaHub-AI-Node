# Changelog

## v0.8.18

- Vollständige Drittanbieter-Lizenzverwaltung ergänzt.
- Direkte Python-Abhängigkeiten in `dependency_licenses.json` dokumentiert.
- Standard-Lizenztexte unter `licenses/` ergänzt.
- Automatische Lizenzprüfung in den Release-Prozess integriert.
- Release bricht bei fehlenden Lizenzinformationen ab.

## v0.8.17

- Windows-Entwicklungsinstallation korrigiert: `uvloop` wird unter Windows automatisch übersprungen.
- Provider-System und AI-Plugin-Engine weiter stabilisiert.
- Geschützte Plugin-API mit API-Token-Unterstützung ergänzt.
- `.mhaiplugin`-Pakete mit Pflichtdateien, Paketprüfung und Lizenzprüfung unterstützt.
- Installationspläne, Preflight-Prüfung, Bestätigung und kontrollierte Ausführung ergänzt.
- Persistenten Planspeicher und Plugin-Verwaltungsendpunkte erweitert.
- Laufzeitpfade konsequent auf `/opt/mediahub/ai-node` umgestellt.
- Installer für Debian 13 „Trixie“ und Raspberry Pi OS 64-Bit vervollständigt.
- Systemweiten Uninstaller mit vollständigem Test-Reset ergänzt.
- Health-Endpunkt um Pluginzahlen und Systemstatus erweitert.
- 79 automatisierte Tests erfolgreich ausgeführt.
- Zahlreiche Stabilitäts-, Token-, Pfad- und Installationskorrekturen.

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
