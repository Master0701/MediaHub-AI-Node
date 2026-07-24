# Wartung

## Regelmäßige Prüfungen

```bash
sudo systemctl status mediahub-ai-node
sudo journalctl -u mediahub-ai-node --since "24 hours ago"
df -h
free -h
```

## Python-Abhängigkeiten

```bash
source /opt/mediahub/venv/bin/activate
pip list --outdated
```

Updates nicht ungeprüft in ein laufendes System übernehmen. Zuerst Tests und
Release-Prüfung ausführen.

## Qualitätsprüfung

```bash
python -m pytest
python -m ruff check .
python release.py
```

## Datenbank

- regelmäßig sichern
- Migrationen dokumentieren
- Integritätsprüfung nach größeren Änderungen durchführen
- alte Backups nach einer festgelegten Aufbewahrungszeit bereinigen
