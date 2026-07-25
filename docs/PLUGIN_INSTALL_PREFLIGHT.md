# Integrierte Installations-Vorabprüfung

`POST /plugins/install` führt die Vorprüfung jetzt automatisch vor jeder
Installation aus.

## Installationsreihenfolge

1. API-Token prüfen
2. Upload und Content-Type prüfen
3. SHA-256 kontrollieren
4. ZIP-Pfade und Manifest validieren
5. Lizenzdatei prüfen
6. Python-Abhängigkeiten prüfen
7. benötigte Tools prüfen
8. Plugin-Abhängigkeiten prüfen
9. vorhandene Version sichern
10. Plugin installieren
11. Registry neu laden

Schlägt einer der Schritte 1 bis 8 fehl, wird nichts installiert und kein
bestehendes Plugin verändert.

## API-Antwort

Eine erfolgreiche Installation enthält zusätzlich:

```json
{
  "preflight": {
    "ready": true,
    "license_present": true,
    "warnings": [],
    "python_requirements": [],
    "required_tools": [],
    "plugin_dependencies": []
  }
}
```

## Aktuelle Einschränkung

Fehlende Python-Pakete und externe Tools werden in dieser Version nur erkannt.
Sie werden noch nicht automatisch installiert. Diese Installation wird später
über kontrollierte, bestätigungspflichtige Installationspläne ergänzt.
