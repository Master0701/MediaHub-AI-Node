# Installation

## Variante A: Installation über Git

```bash
cd /opt/mediahub
git clone https://github.com/Master0701/MediaHub-AI-Node.git ai-node
cd ai-node

python3 -m venv /opt/mediahub/venv
source /opt/mediahub/venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Datenbank vorbereiten, sofern erforderlich:

```bash
python init_database.py
```

Teststart:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8765
```

## Variante B: Installation über Release-ZIP

1. Das passende Release-ZIP und die SHA-256-Datei herunterladen.
2. Prüfsumme kontrollieren.
3. ZIP nach `/opt/mediahub/ai-node` entpacken.
4. Python-Umgebung und Abhängigkeiten installieren.

Beispiel:

```bash
sha256sum -c MediaHub-AI-Node_v0.7.1.zip.sha256
sudo mkdir -p /opt/mediahub/ai-node
sudo unzip -o MediaHub-AI-Node_v0.7.1.zip -d /opt/mediahub/ai-node
sudo chown -R mediahub:mediahub /opt/mediahub/ai-node

cd /opt/mediahub/ai-node
python3 -m venv /opt/mediahub/venv
source /opt/mediahub/venv/bin/activate
pip install -r requirements.txt
```

Danach den systemd-Dienst nach der Anleitung in `SYSTEMD_SERVICE.md` einrichten.
