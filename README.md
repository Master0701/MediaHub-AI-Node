# MediaHub-AI-Node

**MediaHub-AI-Node** ist ein lokaler KI-, Wissens- und Medienanalyse-Knoten für
Raspberry Pi und andere Linux-Systeme. Der Dienst stellt eine REST-API für
MediaHub, MediaHub-Plugins und weitere Clients im Heimnetz bereit.

> **Projektstatus:** frühe, funktionsfähige Entwicklungsfassung  
> **Aktuelle Version:** 0.7.1  
> **Primäre Zielplattform:** Raspberry Pi 5 mit 64-Bit-Linux

## Hauptfunktionen

- lokale REST-API auf Basis von FastAPI
- Betrieb als systemd-Dienst
- Health- und Systemstatus
- Wissensdatenbank für Filme, Serien und spätere Medientypen
- Titel-, Alias- und externe-ID-Erkennung
- Dublettenerkennung und Zusammenführung von Einträgen
- Beziehungen wie Franchise, Fortsetzung, Prequel, Spin-off und Crossover
- Aufgabenwarteschlange und Cache-Grundlage
- Provider-Schicht für lokale, Raspberry-Pi- und optionale Cloud-Backends
- Backup-, Wiederherstellungs- und Wartungsfunktionen

## Zielarchitektur

Der AI-Node bleibt als eigenständiger Dienst nutzbar. MediaHub ist der erste
vorgesehene Client, aber nicht die einzige mögliche Anwendung. Die API wird
deshalb allgemein, modular und erweiterbar aufgebaut.

Geplante Anbindungen umfassen unter anderem:

- MediaHub
- MediaHub WebRemote
- MediaHub Mobile Dashboard
- MediaHub Metadata Editor
- MediaHub-KI-Assistent
- MediaHub Renamer
- MediaHub Hörbuchverwaltung
- MediaHub Cut & Merge
- zukünftige externe Clients

## Schnellstart

```bash
cd /opt/mediahub/ai-node
source /opt/mediahub/venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8765
```

Health-Check:

```bash
curl -sS http://127.0.0.1:8765/health | python -m json.tool
```

API-Dokumentation:

```text
http://127.0.0.1:8765/docs
```

## Installation

- [Raspberry Pi vorbereiten](docs/RASPBERRY_PI_SETUP.md)
- [Installation](docs/INSTALLATION.md)
- [systemd-Dienst](docs/SYSTEMD_SERVICE.md)
- [Update](docs/UPDATE.md)
- [Deinstallation](docs/UNINSTALL.md)

## Betrieb und Entwicklung

- [AI-Node-Handbuch](docs/AI_NODE_GUIDE.md)
- [API](docs/API.md)
- [Wissensdatenbank](docs/KNOWLEDGE_DATABASE.md)
- [Backup und Wiederherstellung](docs/BACKUP_AND_RESTORE.md)
- [Wartung](docs/MAINTENANCE.md)
- [Fehlerbehebung](docs/TROUBLESHOOTING.md)
- [Sicherheit](SECURITY.md)
- [Mitwirken](CONTRIBUTING.md)

## Tests und Release-Prüfung

```bash
python -m pytest
python -m ruff check .
python release.py
```

`release.py` prüft Syntax, Tests und Ruff und erstellt danach das Release-ZIP
sowie die zugehörige SHA-256-Datei.

## Lizenz

MediaHub-AI-Node wird unter der MIT-Lizenz veröffentlicht. Drittanbieter-
Komponenten behalten ihre jeweiligen Lizenzen und Urheberrechte.

- [LICENSE](LICENSE)
- [THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md)
- [`licenses/`](licenses/)
