# Raspberry Pi vorbereiten

## Getestetes System

- Raspberry Pi 5
- Raspberry Pi OS 64-Bit
- Debian 13 „Trixie“
- ARM64 / aarch64
- systemd
- Python 3.13
- SSD

## Linux-Benutzer

Empfohlener Standard: `mediahub`.

Der Installer kann auch einen vorhandenen anderen Benutzer verwenden oder einen neuen Benutzer anlegen. Der gewählte Benutzer wird im systemd-Dienst eingetragen und erhält die nötigen Rechte.

## Vorbereitung

```bash
sudo apt update
sudo apt full-upgrade -y
sudo reboot
```

Danach Repository klonen und installieren:

```bash
git clone https://github.com/Master0701/MediaHub-AI-Node.git
cd MediaHub-AI-Node
sudo ./install.sh
```

## Sicherheit

Schreibende API-Endpunkte werden durch `MEDIAHUB_AI_NODE_API_TOKEN` geschützt. Das Token liegt in `/opt/mediahub/ai-node/.env`.
