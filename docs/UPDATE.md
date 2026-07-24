# Aktualisierung

## Git-Installation

```bash
cd /opt/mediahub/ai-node
./update.sh
```

Das Skript erstellt ein Backup, lädt nur Fast-Forward-Änderungen, aktualisiert
Abhängigkeiten, führt Ruff und Pytest aus, startet den Dienst neu und kontrolliert
den Health-Endpunkt.

## Release-ZIP

Neues Raspberry-Pi-ZIP herunterladen, SHA-256-Prüfsumme prüfen, entpacken und
darin `./install.sh` ausführen. Eine vorhandene `.env` wird nicht überschrieben.
