# Geschützte AI-Plugin-Installations-API

## Endpunkt

```http
POST /plugins/install
```

Der Endpunkt erwartet:

- Bearer-Token
- ZIP-Paket als rohen Request-Body
- SHA-256-Prüfsumme im Header
- optionalen Dateinamen im Header

## Header

```text
Authorization: Bearer <TOKEN>
Content-Type: application/zip
X-Plugin-SHA256: <64-stellige SHA-256-Prüfsumme>
X-Plugin-Filename: provider.ollama.zip
```

## Beispiel mit curl

```bash
curl -X POST \
  http://127.0.0.1:8765/plugins/install \
  -H "Authorization: Bearer $MEDIAHUB_AI_NODE_API_TOKEN" \
  -H "Content-Type: application/zip" \
  -H "X-Plugin-SHA256: $(sha256sum provider.ollama.zip | cut -d' ' -f1)" \
  -H "X-Plugin-Filename: provider.ollama.zip" \
  --data-binary @provider.ollama.zip
```

## Verhalten

1. Token prüfen
2. Upload-Größe prüfen
3. SHA-256 prüfen
4. ZIP und Manifest validieren
5. vorhandenes Plugin sichern
6. neues Plugin kontrolliert installieren
7. Plugin-Registry neu einlesen
8. aktivierte Plugins laden
9. Installationsstatus zurückgeben

## Noch nicht enthalten

- Deinstallation
- manuelles Rollback über REST
- Aktivieren und Deaktivieren über REST
- automatische Python-Abhängigkeiten
- automatische Tool-Installation
- Paketsignaturen
