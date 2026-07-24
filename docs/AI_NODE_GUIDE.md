# MediaHub-KI-Knoten – Allgemeines Handbuch

Aktuelle Version: **0.7.0**

Der MediaHub-KI-Knoten ist ein lokaler Dienst für Medienanalyse,
Wissensverwaltung, Aufgabenwarteschlangen und spätere KI-Funktionen im Heimnetz.

## Wichtige Bereiche

- REST-API auf Port `8765`
- OpenAPI unter `/docs`
- lokale Wissensdatenbank
- Medien- und Dateinamenanalyse
- Provider-Schicht
- Cache-, Modell-, Daten-, Job- und Log-Verzeichnisse
- Health-Check, Backup und Wiederherstellung

## Installation

```bash
git clone https://github.com/Master0701/MediaHub-AI-Node.git
cd MediaHub-AI-Node
./install.sh
```

## Zugriff

- `http://<PI-IP>:8765/health`
- `http://<PI-IP>:8765/docs`
- `http://<PI-IP>:8765/openapi.json`

Der Dienst ist für das lokale Heimnetz gedacht und sollte nicht ungeschützt ins
Internet freigegeben werden.
