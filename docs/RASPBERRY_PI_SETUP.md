# Raspberry Pi vorbereiten

## Voraussetzungen

- Raspberry Pi 5
- 64-Bit Raspberry Pi OS oder kompatibles Debian-Linux
- Netzwerkzugriff im Heimnetz
- ausreichend freier Speicher
- Benutzer `mediahub` mit passenden Rechten

## System aktualisieren

```bash
sudo apt update
sudo apt full-upgrade -y
sudo reboot
```

## Grundpakete installieren

```bash
sudo apt install -y git python3 python3-venv python3-pip unzip curl
```

## Verzeichnisse vorbereiten

```bash
sudo mkdir -p /opt/mediahub/ai-node
sudo chown -R mediahub:mediahub /opt/mediahub
```

## Hinweise

Der Dienst ist zunächst für das lokale Heimnetz vorgesehen. Eine öffentliche
Freigabe sollte erst nach Einrichtung von Authentifizierung, Firewall und
verschlüsselter Verbindung erfolgen.
