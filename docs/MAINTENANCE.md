# Wartung

## Wartungsskript

```bash
cd /opt/mediahub/ai-node
./scripts/health_check.sh
```

Das Skript prüft:

- systemd-Dienst
- REST-Health-Endpunkt
- OpenAPI
- Python und virtuelle Umgebung
- RAM
- SSD-Speicher
- CPU-Temperatur
- optional den Smoke-Test

## Regelmäßiger Ablauf

### Nach Änderungen

```bash
python -m pytest
python tests/test_ai_node_smoke.py
./scripts/backup_ai_node.sh
```

### Wöchentlich

- Logs kontrollieren
- Health-Check ausführen
- freien SSD-Speicher prüfen
- fehlgeschlagene Jobs kontrollieren

### Monatlich

- externes Backup kontrollieren
- SHA-256-Prüfsumme testen
- Wiederherstellungsanleitung prüfen
- Abhängigkeiten und Sicherheitsmeldungen kontrollieren

## Aktualisierungen

Vor Betriebssystem-, Python- oder Datenbankänderungen immer ein aktuelles Backup erstellen.

Keine automatische Aktualisierung einbauen, bevor Rückfallstrategie, Datenbankmigration und Release-Prüfung zuverlässig funktionieren.
