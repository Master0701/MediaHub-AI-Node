# MediaHub-AI-Node – Handbuch

## Zweck

Der AI-Node stellt zentrale KI-, Wissens- und Analysefunktionen als lokalen
Dienst bereit. MediaHub und seine Plugins greifen über eine REST-API darauf zu.

## Grundprinzipien

- eigenständig nutzbarer Dienst
- lokale Verarbeitung bevorzugt
- optionale externe Provider nur nach Konfiguration
- lange Aufgaben über eine Warteschlange
- klare Trennung zwischen API, Wissensdatenbank, Analyse und Providern
- erweiterbar für weitere Medientypen wie Hörbücher

## Betriebsverzeichnis

Empfohlen:

```text
/opt/mediahub/ai-node
```

Virtuelle Python-Umgebung:

```text
/opt/mediahub/venv
```

## Standardport

```text
8765
```

## Wichtige Prüfungen

```bash
sudo systemctl status mediahub-ai-node
curl -sS http://127.0.0.1:8765/health
sudo journalctl -u mediahub-ai-node -n 100 --no-pager
```

## Geplante Erweiterungen

- lokale KI-Modelle und Klassifikatoren
- optionales OpenAI-/Cloud-Backend
- In-Video-Erkennung
- Qualitätsbewertung
- Wissensbeziehungen und Reihenfolgen
- Metadaten- und Bild-Cache
- Status- und Überwachungsoberfläche
