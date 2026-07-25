# Persistente Plugin-Installationspläne

## Zweck

Installationspläne bleiben jetzt auch bei einem Neustart des AI-Node-Dienstes
erhalten. Dadurch kann MediaHub einen bereits angezeigten Plan weiterhin
bestätigen, solange seine Gültigkeitsdauer nicht abgelaufen ist.

## Standardpfad

```text
/opt/mediahub/ai-node/data/plugin_plans
```

Konfigurierbar über:

```text
MEDIAHUB_AI_NODE_PLUGIN_PLAN_DIR
```

## Struktur

```text
data/plugin_plans/
└── <plan_id>/
    ├── plan.json
    └── plugin.zip
```

## Verhalten

- Plan und geprüftes ZIP werden gemeinsam gespeichert.
- Beim Start lädt der AI-Node gültige Pläne wieder ein.
- Beschädigte oder unvollständige Planordner werden entfernt.
- Abgelaufene Pläne werden bereinigt.
- Nach Bestätigung oder Abbruch wird der gesamte Planordner gelöscht.
- Der Plan bleibt weiterhin nur einmal verwendbar.
