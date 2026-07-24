# API

## Interaktive Dokumentation

Bei laufendem Dienst:

```text
http://<PI-IP>:8765/docs
```

OpenAPI-Datei:

```text
http://<PI-IP>:8765/openapi.json
```

## Health-Check

```bash
curl -sS http://127.0.0.1:8765/health
```

## Grundregeln

- Clients sollten Timeouts setzen.
- Lange Analysen sollen über Jobs und Statusabfragen laufen.
- Fehlerantworten müssen maschinenlesbar bleiben.
- Zukünftige schreibende oder sensible Endpunkte benötigen Authentifizierung.
- API-Versionen sollen bei inkompatiblen Änderungen klar getrennt werden.

Die tatsächlich verfügbaren Endpunkte sind jederzeit in der automatisch
erzeugten OpenAPI-Dokumentation sichtbar.
