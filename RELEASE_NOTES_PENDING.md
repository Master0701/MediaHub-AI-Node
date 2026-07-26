# MediaHub-AI-Node v0.8.17

## Änderungen

- Windows-Entwicklungsumgebung unterstützt: `uvloop` wird dort automatisch ausgelassen.
- Provider-System und AI-Plugin-Engine stabilisiert.
- Geschützte REST-API mit API-Token-Unterstützung.
- `.mhaiplugin`-Pakete inklusive Pflichtdateien, Preflight-, Paket-, Lizenz- und Abhängigkeitsprüfung.
- Installationspläne mit Bestätigung, Speicherung und kontrollierter Ausführung.
- Laufzeitpfade auf `/opt/mediahub/ai-node` vereinheitlicht.
- Automatischer Installer für Debian 13 „Trixie“ und Raspberry Pi OS 64-Bit.
- Systemweiter Uninstaller für vollständige Test- und Produktionsdeinstallation.
- Health-Endpunkt mit Plugin-, CPU-, RAM-, Datenträger- und Temperaturstatus.
- 79 automatisierte Tests erfolgreich.

## Getestete Plattform

- Raspberry Pi 5
- Raspberry Pi OS 64-Bit / Debian 13 „Trixie“
- Python 3.13
- systemd

## Installation über Release-ZIP

```bash
unzip MediaHub-AI-Node_v0.8.17.zip
cd MediaHub-AI-Node_v0.8.17
sudo ./install.sh
```

## Installation über Git

```bash
git clone https://github.com/Master0701/MediaHub-AI-Node.git
cd MediaHub-AI-Node
sudo ./install.sh
```

## Deinstallation

```bash
sudo mediahub-ai-node-uninstall
```

Vollständiger Test-Reset:

```bash
sudo mediahub-ai-node-uninstall --purge --remove-venv --yes
```

## Hinweis

Die Dateien „Source code (zip)“ und „Source code (tar.gz)“ werden automatisch
von GitHub erzeugt. Für eine normale Installation sollte bevorzugt das
bereitgestellte Release-ZIP verwendet werden.
