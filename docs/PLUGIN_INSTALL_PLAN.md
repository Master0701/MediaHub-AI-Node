# Bestätigungspflichtiger Installationsplan

## Zweck

Fehlende Voraussetzungen werden nicht automatisch installiert. Stattdessen
erzeugt der AI-Node zunächst einen Plan, den MediaHub anzeigen und vom Benutzer
bestätigen lassen kann.

## Beispiel

```json
{
  "plugin_id": "analyzer.video",
  "ready_without_changes": false,
  "missing_count": 3,
  "requires_confirmation": true,
  "requires_restart": false,
  "actions": [
    {
      "type": "python_package",
      "name": "sentence-transformers>=3.0",
      "reason": "Benötigtes Python-Paket ist nicht installiert.",
      "command_preview": "python -m pip install sentence-transformers>=3.0"
    },
    {
      "type": "system_tool",
      "name": "tesseract-ocr",
      "reason": "Benötigtes Systemwerkzeug ist nicht verfügbar.",
      "command_preview": "sudo apt install tesseract-ocr"
    },
    {
      "type": "ai_plugin",
      "name": "provider.base",
      "reason": "Benötigtes AI-Plugin ist nicht installiert.",
      "command_preview": null
    }
  ]
}
```

## Geplanter Ablauf in MediaHub

1. Benutzer klickt im Reiter `AI-Plugins` auf Installieren.
2. MediaHub lädt das Paket bzw. den Katalogeintrag.
3. Der AI-Node erzeugt den Installationsplan.
4. MediaHub zeigt alle geplanten Änderungen.
5. Benutzer bestätigt oder bricht ab.
6. Erst nach Bestätigung werden freigegebene Schritte ausgeführt.

## Noch nicht enthalten

- REST-Endpunkt für Planerstellung
- automatische Paketgrößen
- Downloadquellen
- Lizenztexte pro Abhängigkeit
- tatsächliche Ausführung des Plans
- Bestätigungs-Token oder Plan-ID
