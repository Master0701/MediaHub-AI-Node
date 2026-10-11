# MediaHub-AI-Node v0.8.26

## Plugin-Backups und Wiederherstellung

- Neue API `GET /plugins/backups/overview` zur Ermittlung aller Plugin-IDs mit vorhandenen Backups.
- Backups können auch dann gefunden werden, wenn das zugehörige Plugin nicht mehr installiert ist.
- Erweiterung des Plugin-Installers um die Erkennung vorhandener Backup-Verzeichnisse.
- Korrektur der Backup-Erstellungszeit anhand des tatsächlichen UTC-Zeitstempels in der Backup-ID.
- Fallback auf den Dateisystem-Zeitstempel für ältere Backup-Namen.
- Bereitstellung der korrigierten Backup-Daten für die MediaHub-Oberfläche.
- Vorhandene Backup-, Wiederherstellungs- und Löschfunktionen bleiben erhalten.

## Verbesserte Plugin-Plan-Ausführung

- Korrekte Übergabe verwalteter Runtime- und Modellinstallationen an den bestätigten Plugin-Installer.
- Unterstützung für die verwalteten Plugins GLiNER und SmolVLM2.
- Unterstützte Installationspläne können den Status `ready_for_confirmation` erhalten.
- Ausstehende verwaltete Aktionen werden als `deferred_to_confirmation` ausgewiesen.
- Die Aktionen bleiben im ursprünglichen Installationsplan sichtbar.
- Keine vorzeitige Installation verwalteter Voraussetzungen während der allgemeinen Plan-Ausführung.
- Fremde Plugins, Systemtools und Installationspläne ohne erforderliche Lizenzfreigabe werden nicht automatisch für die Bestätigung freigegeben.
- Die bestehende authentifizierte Installationsbestätigung bleibt für die eigentliche Installation zuständig.

## Windows Compute Node v0.1.2

- Keine Änderungen an Windows Compute Node und Speech-Runtime.
- Die bestehende Windows-Version 0.1.2 bleibt erhalten.

## Tests und Validierung

- Sieben Regressionstests für die Plugin-Plan-Ausführung erfolgreich.
- Acht Tests des Plugin-Installers erfolgreich.
- Zwölf weitere Plugin-API- und Installations-API-Tests erfolgreich.
- Insgesamt 27 relevante automatisierte Tests erfolgreich.
- GLiNER v0.1.1 nach Deinstallation erfolgreich aus einem Backup wiederhergestellt.
- Backup-Erkennung bei nicht installiertem Plugin erfolgreich geprüft.
- Backup-Zeitstempel über die laufende AI-Node-API kontrolliert.
- Python-Syntaxprüfung und Git-Diff-Prüfung erfolgreich.

## Kompatibilität

- MediaHub GLiNER v0.1.1
- MediaHub SmolVLM2 Vision v0.1.1
- MediaHub-Hauptprogramm v1.0.24 mit erweiterter Backup-Verwaltung

## Unverändert

- Raspberry-Pi-Online-Installer
- Windows Compute Node und Speech-Runtime
- Bestehende Plugin-Pakete
