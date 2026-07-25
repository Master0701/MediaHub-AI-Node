# AI-Plugin-Installer: Backup und Rollback

## Zweck

Der Installer baut auf der vorhandenen Paketprüfung auf und führt erst nach
erfolgreicher Validierung eine Installation aus.

## Ablauf

1. ZIP und SHA-256 prüfen
2. Manifest validieren
3. Paket in ein temporäres Verzeichnis entpacken
4. Inhalt in einen temporären Zielordner kopieren
5. vorhandenes Plugin sichern
6. neuen Stand atomar an den Zielort verschieben
7. bei Fehlern den vorherigen Stand wiederherstellen

## Standard-Zielbereiche

Vorgesehen:

```text
/opt/mediahub/ai-node/plugins
/opt/mediahub/ai-node/backups/plugins
```

## Backup-Struktur

```text
backups/plugins/
└── provider.test/
    └── 20260725T120000000000Z/
        ├── plugin.json
        └── plugin.py
```

## Sicherheitsregeln

- Installationspfade müssen innerhalb des Plugin-Verzeichnisses liegen.
- Backup-Pfade müssen innerhalb des Backup-Verzeichnisses liegen.
- Plugin-Pakete werden vor dem Entpacken vollständig geprüft.
- Bestehende Plugins werden vor dem Ersetzen gesichert.
- Ein fehlerhafter Installationsvorgang soll den vorherigen Stand erhalten.

## Noch nicht enthalten

- REST-Endpunkte
- automatische Abhängigkeitsinstallation
- Aktivierung oder Deaktivierung
- Dienstneustart
- Bereinigung alter Backups
- Signaturprüfung
