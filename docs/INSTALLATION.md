# Installation

## Direkt aus GitHub

```bash
git clone https://github.com/Master0701/MediaHub-AI-Node.git
cd MediaHub-AI-Node
./install.sh
```

## Aus einem GitHub-Release

1. `MediaHub-AI-Node_vX.Y.Z_RaspberryPi.zip` herunterladen.
2. Zugehörige SHA-256-Datei prüfen.
3. ZIP entpacken.
4. Im entpackten Ordner `./install.sh` ausführen.

## Standardwerte

- Projekt: `/opt/mediahub/ai-node`
- Python-Umgebung: `/opt/mediahub/venv`
- Konfiguration: `/opt/mediahub/ai-node/.env`
- Dienst: `mediahub-ai-node`
- Port: `8765`

Eine vorhandene `.env` wird nicht überschrieben.
