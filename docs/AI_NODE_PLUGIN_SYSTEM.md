# AI-Node-Plugin-System

## Ziel

AI-Plugins werden künftig im Repository `MediaHub_Plugins` veröffentlicht,
aber auf dem verbundenen MediaHub-AI-Node installiert und ausgeführt.

MediaHub zeigt dafür im Plugin-Store zwei getrennte Bereiche:

- MediaHub-Plugins
- AI-Plugins

## Plugin-Verzeichnis auf dem AI-Node

Vorgesehen:

```text
/opt/mediahub/ai-node/plugins/
```

Jedes Plugin besitzt einen eigenen Unterordner:

```text
plugins/
└── provider_ollama/
    ├── plugin.json
    ├── plugin.py
    ├── requirements.txt
    ├── LICENSE
    └── README.md
```

## Manifest

Minimalbeispiel:

```json
{
  "id": "provider.ollama",
  "name": "Ollama Provider",
  "version": "1.0.0",
  "type": "provider",
  "entrypoint": "plugin:OllamaPlugin",
  "api_version": "1",
  "license": "MIT",
  "enabled_by_default": true,
  "capabilities": ["text_generation", "embedding"],
  "required_tools": ["ollama"]
}
```

## Unterstützte Plugin-Typen

- provider
- ocr
- audio
- video
- analyzer
- knowledge
- cache
- model
- utility

## Sicherheitsmodell

Die aktuelle Engine erkennt und lädt lokale Plugins. Die spätere Installation
über MediaHub benötigt zusätzlich:

- authentifizierte AI-Node-Verbindung
- SHA-256-Prüfung
- sichere ZIP-Pfadprüfung
- Signatur oder vertrauenswürdigen Katalog
- Lizenzprüfung
- Abhängigkeitsprüfung
- Backup und Rollback
- kontrollierten Dienstneustart

Die Installations-API wird deshalb erst in einem eigenen Schritt ergänzt.
