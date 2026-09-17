# MediaHub-AI-Node v0.8.21

## MediaHub-AI-Node 0.8.21

- Job-API um einen vorbereitenden `preparing`-Status erweitert.
- Sicheren Upload von Job-Eingabedateien über die Job-API ergänzt.
- Jobs werden erst nach vollständig erfolgreichem Input-Upload zur Ausführung freigegeben.
- Unvollständige Uploads werden über temporäre `.part`-Dateien abgesichert.
- Job-Payload und Input-Informationen werden nach erfolgreichem Upload gemeinsam aktualisiert.
- Gemeinsame Job-Verarbeitung für die Dateiübergabe an Compute-Nodes vorbereitet.

## Windows Compute Node 0.1.1

- Temporäre Job-Eingabedateien werden nach abgeschlossenen, fehlgeschlagenen oder abgebrochenen Jobs automatisch bereinigt.
- Neue zentrale `JobInputCleanup`-Komponente für die sichere Bereinigung von `runtime/job_inputs` ergänzt.
- Verwaiste Job-Eingaben aus vorherigen Prozessen werden beim Start des Compute Nodes automatisch entfernt.
- Sicherheitsprüfung verhindert, dass die Job-Bereinigung das vorgesehene `job_inputs`-Verzeichnis verlassen kann.
- Dispatcher um Runtime-Verzeichnis und Job-Input-Lifecycle erweitert.
- Job-Queue und API für vorbereitete Datei-Jobs erweitert.
- Plugin-Loader und Compute-Node-API für die Dateiübergabe und Job-Ausführung erweitert.
- Dispatcher-Tests an das Runtime-Verzeichnis angepasst.
- Startup-Cleanup mit der gebauten Windows-EXE erfolgreich geprüft.
- Vollständiger Testlauf erfolgreich: 216 Tests bestanden, 2 Tests übersprungen.
