# Vorhandenen Raspberry-Pi-Stand in das Repository übernehmen

Dieses Grundpaket enthält bewusst keinen erfundenen Ersatz für den bereits getesteten `app/`-Code.

## Auf dem Raspberry Pi

```bash
cd /opt/mediahub/ai-node
git status
```

Vor der Übernahme:

1. aktuelles Backup erstellen
2. Smoke-Test ausführen
3. Geheimnisse und Laufzeitdaten identifizieren
4. `.gitignore` prüfen
5. `app/`, `tests/` und vorhandene Skripte in das Repository übernehmen
6. `requirements.txt` mit den tatsächlich benötigten direkten Abhängigkeiten abgleichen
7. Lizenzprüfung durchführen

## Nicht einchecken

- `.env`
- API-Schlüssel
- Datenbanken mit privaten Daten
- Cache
- Modelle
- Logs
- Backups
- virtuelle Umgebung
- Zugangsdaten

## Empfohlene erste Veröffentlichung

```text
v0.1.0
```

Die erste Veröffentlichung sollte als Alpha oder Pre-Release markiert werden, bis Installation auf einem zweiten, sauberen System erfolgreich getestet wurde.
