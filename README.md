# MediaHub-AI-Node

**MediaHub-AI-Node** ist ein lokaler KI- und Medienanalyse-Knoten für Raspberry Pi und andere Linux-Systeme. Er stellt eine REST-API für MediaHub, MediaHub-Plugins und andere Clients im Heimnetz bereit.

> Projektstatus: frühe, funktionsfähige Entwicklungsfassung. Der vorhandene Raspberry-Pi-5-Teststand enthält Health-API, Wissensdatenbank, Import-, Merge- und Beziehungsfunktionen, Graphprüfung, Backup und Wiederherstellung.

## Hauptfunktionen

- lokale REST-API
- systemd-Dienst
- Health- und Systemstatus
- Wissensdatenbank für Filme, Serien und spätere Medientypen
- Titel-, Alias- und externe-ID-Erkennung
- Dublettenerkennung und Merge
- Beziehungen wie Franchise, Fortsetzung, Prequel und Spin-off
- Aufgabenwarteschlange und Cache-Grundlage
- Provider-Schicht für lokale, Raspberry-Pi- und optionale Cloud-Backends
- Backup-, Restore- und Wartungsskripte

## Zielarchitektur

MediaHub-AI-Node soll unabhängig nutzbar bleiben. MediaHub ist der erste Client, aber nicht die einzige mögliche Anwendung. Die API wird deshalb allgemein und erweiterbar gehalten.

## Schnellstart

Die vollständige Anleitung steht in [`docs/INSTALLATION.md`](docs/INSTALLATION.md).

```bash
python3 -m venv /opt/mediahub/venv
source /opt/mediahub/venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8765
```

Health-Check:

```bash
curl -sS http://127.0.0.1:8765/health | python -m json.tool
```

## Dokumentation

- [Raspberry Pi vorbereiten](docs/RASPBERRY_PI_SETUP.md)
- [Installation](docs/INSTALLATION.md)
- [Backup und Wiederherstellung](docs/BACKUP_AND_RESTORE.md)
- [systemd-Dienst](docs/SYSTEMD_SERVICE.md)
- [API](docs/API.md)
- [Wissensdatenbank](docs/KNOWLEDGE_DATABASE.md)
- [Wartung](docs/MAINTENANCE.md)
- [Fehlerbehebung](docs/TROUBLESHOOTING.md)
- [Sicherheit](SECURITY.md)
- [Mitwirken](CONTRIBUTING.md)

## Öffentliche Nutzung

Das Projekt wird unter der MIT-Lizenz veröffentlicht. Drittanbieter-Komponenten behalten ihre jeweiligen Lizenzen. Siehe [`THIRD_PARTY_LICENSES.md`](THIRD_PARTY_LICENSES.md).

## Repository-Struktur

```text
MediaHub-AI-Node/
├── app/
├── docs/
├── examples/
├── scripts/
├── tests/
├── .github/workflows/
├── requirements.txt
├── pyproject.toml
├── LICENSE
└── README.md
```

## Aktuell bestätigter Teststand

Am 22. Juli 2026 endete der automatische Abschlusstest des Raspberry-Pi-Knotens mit:

```text
Bestanden: 5 von 5
Gesamtergebnis: ERFOLGREICH
```

Geprüft wurden Health-API, OpenAPI-Endpunkte, Wissenseintrag-Import, Beziehungsimport und Graph-Integrität.
