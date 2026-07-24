# Fehlerbehebung

## Dienst startet nicht

```bash
sudo systemctl status mediahub-ai-node
sudo journalctl -u mediahub-ai-node -n 100 --no-pager
```

## Port 8765 bereits belegt

```bash
sudo ss -ltnp | grep 8765
```

## Python-Modul fehlt

```bash
source /opt/mediahub/venv/bin/activate
pip install -r requirements.txt
```

## Health-Check schlägt fehl

```bash
curl -v http://127.0.0.1:8765/health
```

Danach prüfen:

- läuft der Dienst?
- stimmt der Port?
- blockiert eine Firewall?
- wurde die richtige virtuelle Umgebung verwendet?
- enthält das Protokoll einen Python-Fehler?

## Nach Update treten Fehler auf

```bash
git status
python -m pytest
python -m ruff check .
```

Bei Datenbankproblemen zuerst ein Backup erstellen und keine unkontrollierten
Reparaturbefehle ausführen.
