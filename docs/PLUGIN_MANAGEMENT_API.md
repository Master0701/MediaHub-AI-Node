# Geschützte AI-Plugin-Verwaltungs-API

Alle schreibenden und sensiblen Verwaltungsendpunkte benötigen:

```text
Authorization: Bearer <MEDIAHUB_AI_NODE_API_TOKEN>
```

## Aktivieren

```http
POST /plugins/{plugin_id}/enable
```

## Deaktivieren

```http
POST /plugins/{plugin_id}/disable
```

## Entfernen

```http
DELETE /plugins/{plugin_id}
```

Standardmäßig wird vor der Entfernung ein Backup erstellt.

Ohne Backup:

```http
DELETE /plugins/{plugin_id}?create_backup=false
```

## Backups anzeigen

```http
GET /plugins/{plugin_id}/backups
```

## Rollback

```http
POST /plugins/{plugin_id}/rollback/{backup_name}
```

## Sicherheit

- alle Verwaltungsendpunkte sind tokenpflichtig
- Backup-Namen dürfen keine Pfadbestandteile enthalten
- Installations- und Backup-Pfade bleiben auf erlaubte Verzeichnisse begrenzt
- nach jeder Änderung wird die Plugin-Registry neu aufgebaut
- aktivierte Plugins werden danach erneut geladen

## Noch offen

- Signaturprüfung
- Abhängigkeitsinstallation
- externe Tools
- kontrollierter Dienstneustart
- Backup-Aufbewahrungsregeln
- Rollen und getrennte Berechtigungen
