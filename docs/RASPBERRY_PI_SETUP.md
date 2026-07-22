# Raspberry Pi 5 vorbereiten

## Empfohlene Hardware

- Raspberry Pi 5
- 64-Bit-fähiges Raspberry Pi OS
- SSD statt microSD für Datenbank, Cache und spätere Modelle
- stabiles Netzteil
- kabelgebundenes Netzwerk, wenn möglich
- ausreichende Kühlung

## Raspberry Pi OS installieren

1. Raspberry Pi Imager öffnen.
2. Raspberry Pi OS Lite oder Desktop 64-Bit auswählen.
3. SSD als Ziel auswählen.
4. Hostname festlegen, beispielsweise `mediahub-pi`.
5. SSH aktivieren.
6. Benutzer und sicheres Passwort festlegen.
7. Zeitzone und Tastatur einstellen.
8. Image schreiben und den Pi starten.

## System aktualisieren

```bash
sudo apt update
sudo apt full-upgrade -y
sudo reboot
```

## Grundpakete

```bash
sudo apt install -y \
  python3 \
  python3-venv \
  python3-pip \
  curl \
  git \
  tar
```

Für spätere Video- und Audioanalyse:

```bash
sudo apt install -y ffmpeg
```

## Benutzer und Verzeichnisse

```bash
sudo useradd \
  --system \
  --create-home \
  --shell /bin/bash \
  mediahub 2>/dev/null || true

sudo mkdir -p /opt/mediahub/ai-node
sudo chown -R mediahub:mediahub /opt/mediahub
```

## Netzwerk

Der aktuelle Standardport ist `8765`. Der Dienst ist für das Heimnetz vorgesehen. Keine Portweiterleitung ins Internet einrichten, solange Authentifizierung und Absicherung nicht vollständig konfiguriert sind.
