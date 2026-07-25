# AI-Node-Plugin-API

Die erste Plugin-API ist absichtlich schreibgeschützt.

## Endpunkte

```http
GET /plugins
GET /plugins/{plugin_id}
GET /health
```

`GET /plugins` listet erkannte Plugins und deren Zustand.

`GET /plugins/{plugin_id}` liefert Details zu einem Plugin. Nicht gefundene
Plugins liefern HTTP 404.

`GET /health` enthält zusätzlich die Zähler:

- detected
- enabled
- loaded
- errors

## Standardpfade

```text
/opt/mediahub/ai-node/plugins
/opt/mediahub/ai-node/data/plugin_state.json
```

Die Pfade können über diese Umgebungsvariablen geändert werden:

- `MEDIAHUB_AI_NODE_PLUGINS_DIR`
- `MEDIAHUB_AI_NODE_PLUGIN_STATE_FILE`

Installation, Update, Entfernung und Aktivierung über REST bleiben bis zur
Einführung von Authentifizierung, Prüfsummen, Rollback und Lizenzprüfung
gesperrt.
