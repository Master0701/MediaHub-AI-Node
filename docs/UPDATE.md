# Update

## Vor dem Update

```bash
cd /opt/mediahub/ai-node
git status
```

Lokale Änderungen sollten zuerst gesichert oder eingecheckt werden.

## Git-Installation aktualisieren

```bash
cd /opt/mediahub/ai-node
git pull --ff-only origin main

source /opt/mediahub/venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt

sudo systemctl restart mediahub-ai-node
sudo systemctl status mediahub-ai-node
```

## Update über ZIP

Vor dem Überschreiben ein Backup anlegen. Danach das Update-ZIP direkt im
Projektordner entpacken:

```bash
cd /opt/mediahub/ai-node
unzip -o /pfad/zum/Update.zip
```

Anschließend Abhängigkeiten aktualisieren und den Dienst neu starten.

## Kontrolle

```bash
curl -sS http://127.0.0.1:8765/health | python -m json.tool
python -m pytest
python -m ruff check .
```
