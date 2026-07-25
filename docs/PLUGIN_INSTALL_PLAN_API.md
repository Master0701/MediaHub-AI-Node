# Installationsplan-API

## Endpunkt

```http
POST /plugins/plan
```

Der Endpunkt prüft ein Plugin-ZIP und erzeugt einen Installationsplan. Er
entpackt und installiert das Plugin nicht.

## Benötigte Header

```text
Authorization: Bearer <TOKEN>
Content-Type: application/zip
X-Plugin-SHA256: <SHA-256>
X-Plugin-Filename: plugin.zip
```

## Beispielantwort

```json
{
  "status": "plan_created",
  "package": {
    "plugin_id": "provider.ollama",
    "name": "Ollama Provider",
    "version": "1.0.0",
    "type": "provider",
    "sha256": "...",
    "file_count": 5,
    "uncompressed_size": 12345
  },
  "plan": {
    "ready_without_changes": false,
    "missing_count": 1,
    "requires_confirmation": true,
    "actions": [
      {
        "type": "system_tool",
        "name": "ollama",
        "reason": "Benötigtes Systemwerkzeug ist nicht verfügbar."
      }
    ]
  }
}
```

Der Plan-Endpunkt darf fehlende Voraussetzungen melden. Der eigentliche
Installationsendpunkt bleibt dagegen streng und lehnt unvollständige Pakete ab.
