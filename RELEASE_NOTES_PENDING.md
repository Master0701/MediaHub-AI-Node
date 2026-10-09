# MediaHub-AI-Node v0.8.24

## Änderungen

- Persistente Plugin-Backups für Update, Entfernung und Rollback.
- Gesicherte Wiederherstellung früherer Plugin-Versionen.
- Neuer token-geschützter DELETE-Endpunkt zum gezielten Löschen einzelner Plugin-Backups.
- Andere vorhandene Backups bleiben beim Löschen erhalten.
- Verbesserte Fehlerbehandlung und Sicherheit beim Plugin-Rollback.

## Installation und Dokumentation

- Raspberry-Pi-Installationsanleitung aktualisiert.
- Raspberry-Pi-Update-Anleitung korrigiert und erweitert.
- Raspberry-Pi-Deinstallationsanleitung aktualisiert.
- Dokumentationsindex mit den Anleitungen ergänzt.
- install.sh wird jetzt in das Release-ZIP aufgenommen.
- Release-Prüfung kontrolliert die erforderlichen Anleitungen und den Installer.

## Windows Compute Node

- Windows Compute Node bleibt unverändert auf Version 0.1.2.
- Der bestehende Raspberry-Pi-Online-Installer wurde nicht verändert.

## Getestet

- Ruff-Prüfung erfolgreich.
- Vollständige Testsuite: 221 bestanden, 2 übersprungen.
- HTTP-Test für Backup-Löschung und API-Token-Schutz erfolgreich.
- Git-Diff-Prüfung erfolgreich.
