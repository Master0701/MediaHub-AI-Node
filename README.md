# MediaHub-AI-Node

**MediaHub-AI-Node** ist ein optionaler lokaler KI-, Wissens- und Medienanalyse-Knoten für Raspberry Pi und andere Linux-Systeme.

> **Projektstatus:** funktionsfähige Entwicklungsfassung
> **Primäre Zielplattform:** Raspberry Pi 5 mit Raspberry Pi OS 64-Bit
> **Getestete Basis:** Debian 13 „Trixie“, systemd und Python 3.13

## Rolle im MediaHub-System

Die interne MediaHub-KI bleibt die zentrale Orchestrierungs- und Entscheidungsinstanz. Der Raspberry-Pi-AI-Node ist nur ein optionaler zusätzlicher Ausführungsknoten. Ist er nicht vorhanden oder offline, übernimmt die interne MediaHub-KI die Aufgaben lokal, soweit die benötigten Werkzeuge verfügbar sind.

Nur die interne MediaHub-KI muss das Desktopprogramm selbst steuern. Analyse-, Provider-, OCR-, Audio-, Fingerprint- und ähnliche Funktionen sollen auf beiden Seiten möglichst gleich nutzbar sein.

## Getestete Plattform

- Raspberry Pi 5
- Raspberry Pi OS 64-Bit
- Debian 13 „Trixie“
- ARM64 / aarch64
- systemd
- Python 3.13
- SSD-Installation unter `/opt/mediahub`
- REST-API auf Port `8765`

Der Installer setzt derzeit ein Debian-basiertes System mit `apt` und `systemd` voraus. Andere Debian-13- und Ubuntu-Systeme können funktionieren, wurden aber noch nicht vollständig getestet.

## Installation

```bash
sudo ./install.sh
```

Der Installer verwendet einen frei wählbaren Linux-Benutzer, schlägt standardmäßig `mediahub` vor, erzeugt ein sicheres API-Token, richtet Verzeichnisse und Rechte ein, installiert den systemd-Dienst und prüft Health- sowie geschützten Plugin-Zugriff.

- [Raspberry Pi vorbereiten](docs/RASPBERRY_PI_SETUP.md)
- [Installation](docs/INSTALLATION.md)
- [systemd-Dienst](docs/SYSTEMD_SERVICE.md)
- [Deinstallation](docs/UNINSTALL.md)
- [Release-Checkliste](RELEASE_CHECKLIST.md)

## Automatische Installation durch MediaHub

Die vollständige automatische Installation aus MediaHub wird vorbereitet. MediaHub soll künftig bei Auswahl eines AI-Plugins prüfen, ob ein AI-Node vorhanden ist, bei Bedarf SSH-Daten abfragen, den Node installieren, das erzeugte Token übernehmen und danach das ausgewählte `.mhaiplugin` installieren.

Das SSH-Passwort wird nicht dauerhaft gespeichert.

## Werkzeug- und Abhängigkeitsverwaltung

MediaHub und AI-Node sollen eine gemeinsame Werkzeugverwaltung verwenden. Plugins melden benötigte Werkzeuge und Pakete an. Gemeinsam genutzte Werkzeuge werden referenzgezählt und erst entfernt, wenn kein Plugin sie mehr benötigt.

## Tests

```bash
python -m pytest
python -m ruff check .
python release.py
```

## Lizenz

MIT-Lizenz. Drittanbieter-Komponenten behalten ihre jeweiligen Lizenzen.
