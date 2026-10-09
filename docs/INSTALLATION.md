# MediaHub-AI-Node auf dem Raspberry Pi installieren

## Voraussetzungen

Die dokumentierte Zielplattform ist ein Raspberry Pi 5 mit Raspberry Pi OS 64-Bit bzw. Debian 13 (Trixie), ARM64, `apt`, `systemd` und Python 3.13. Die Installation verwendet standardmäßig `/opt/mediahub/ai-node` und die virtuelle Python-Umgebung `/opt/mediahub/venv`.

Der Installer benötigt Root-Rechte und eine Internetverbindung für System- und Python-Pakete.

## Empfohlene Online-Installation über GitHub

```bash
sudo apt-get update
sudo apt-get install -y git

git clone https://github.com/Master0701/MediaHub-AI-Node.git
cd MediaHub-AI-Node
sudo ./install.sh
```

Der Installer fragt nach dem Linux-Benutzer (Vorgabe `mediahub`) und richtet Systempakete, Python-Umgebung, Dienst, Laufzeitordner und API-Token ein. Einen bereits bestehenden Benutzer kann man auswählen.

Für eine bewusst nicht-interaktive Installation:

```bash
sudo MEDIAHUB_NONINTERACTIVE=1 MEDIAHUB_USER=mediahub ./install.sh
```

## Installation aus einem GitHub-Release

Das zur gewünschten Version gehörende ZIP und seine `.sha256`-Datei von der [Release-Seite](https://github.com/Master0701/MediaHub-AI-Node/releases) herunterladen und in denselben Ordner legen. Dateinamen durch die tatsächlich heruntergeladene Version ersetzen.

```bash
sha256sum -c MediaHub-AI-Node_vVERSION.zip.sha256
unzip MediaHub-AI-Node_vVERSION.zip
cd MediaHub-AI-Node_vVERSION
sudo ./install.sh
```

**Hinweis:** Vor dieser Installationsart prüfen, ob das heruntergeladene Release-Paket `install.sh` enthält. Der derzeitige Paketbau in `release.py` führt `install.sh` nicht in seiner `INCLUDED`-Liste; bis dies im Release-Prozess korrigiert und getestet ist, die GitHub-Quellcode-Installation oben verwenden.

## Installationsorte

- Anwendung und Plugins: `/opt/mediahub/ai-node/`
- Python-Umgebung: `/opt/mediahub/venv/`
- Einstellungen und API-Token: `/opt/mediahub/ai-node/.env`
- Systemdienst: `mediahub-ai-node.service`
- HTTP-Port: `8765` (Standard)

Die `.env` ist vertraulich und darf nicht veröffentlicht werden. Das vom Installer erzeugte Token wird dort gespeichert; die Datei erhält Modus `600`.

## Funktion prüfen

```bash
sudo systemctl status mediahub-ai-node --no-pager
curl -fsS http://127.0.0.1:8765/health
sudo journalctl -u mediahub-ai-node -n 50 --no-pager
```

Der Dienst sollte aktiv sein und `/health` antworten. Schreibende API-Aufrufe benötigen ein gültiges Bearer-Token.

## Weiterführende Anleitungen

- [Update einer vorhandenen Installation](UPDATE.md)
- [Deinstallation](UNINSTALL.md)
- [Backup und Wiederherstellung](BACKUP_AND_RESTORE.md)
