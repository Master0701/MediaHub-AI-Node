# Installation

## Getestete Plattform

- Raspberry Pi 5
- Raspberry Pi OS 64-Bit
- Debian 13 „Trixie“
- ARM64 / aarch64
- systemd
- Python 3.13
- SSD-Installation unter `/opt/mediahub`

Der Installer setzt derzeit `apt` und `systemd` voraus.

## Empfohlene Installation

```bash
sudo ./install.sh
```

Der Installer fragt nach dem Linux-Benutzer. Standard ist `mediahub`; ein vorhandener anderer Benutzer kann ebenfalls verwendet oder auf Wunsch neu angelegt werden.

Automatisch erledigt werden:

- Systempakete und Python-Umgebung
- Abhängigkeiten
- Laufzeitverzeichnisse
- `.env` und `MEDIAHUB_AI_NODE_API_TOKEN`
- Rechte und Eigentümer
- systemd-Dienst
- Health- und geschützter API-Test

Nicht interaktiv:

```bash
sudo MEDIAHUB_NONINTERACTIVE=1 MEDIAHUB_USER=mediahub ./install.sh
```

Mit anderem Benutzer:

```bash
sudo MEDIAHUB_NONINTERACTIVE=1 MEDIAHUB_USER=matthias ./install.sh
```

## Installation über Git

```bash
git clone https://github.com/Master0701/MediaHub-AI-Node.git
cd MediaHub-AI-Node
sudo ./install.sh
```

## Installation über Release-ZIP

```bash
sha256sum -c MediaHub-AI-Node_vVERSION.zip.sha256
unzip MediaHub-AI-Node_vVERSION.zip
cd MediaHub-AI-Node_vVERSION
sudo ./install.sh
```

## API-Token

Das Token wird in `/opt/mediahub/ai-node/.env` gespeichert. Die Datei erhält Modus `600` und gehört dem gewählten AI-Node-Benutzer.

## Automatische Installation aus MediaHub

MediaHub soll künftig den Node über SSH installieren, das Token übernehmen, den Node prüfen und danach das ausgewählte `.mhaiplugin` installieren. Das SSH-Passwort wird nicht gespeichert.
