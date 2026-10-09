# MediaHub-AI-Node vom Raspberry Pi deinstallieren

Die Deinstallation betrifft den **Raspberry-Pi-AI-Node**, nicht die separat entwickelte Windows Compute Node.

## Vorher sichern

Der installierte Uninstaller kann bei der normalen Deinstallation die Daten, Modelle, Backups und `.env` sichern. Bei wichtigen Installationen zusätzlich eine eigene Sicherung anlegen und deren Inhalt prüfen. Besonders wichtig sind `plugins/`, `data/`, `backups/`, `models/` und `.env`.

## Normale Deinstallation

Der Installer richtet den systemweiten Befehl `mediahub-ai-node-uninstall` ein:

```bash
sudo mediahub-ai-node-uninstall
```

Der Uninstaller stoppt und deaktiviert den Dienst, entfernt die systemd-Dienstdateien und den Programmordner `/opt/mediahub/ai-node`. Ohne `--purge` bietet er eine Sicherung der Daten an. Die virtuelle Umgebung `/opt/mediahub/venv` bleibt standardmäßig bestehen. Der Linux-Benutzer wird nicht gelöscht.

Sicherungen aus dem Uninstaller werden unter einem Ordner nach dem Muster `/opt/mediahub/ai-node-preserved-YYYYMMDD-HHMMSS` abgelegt. Den genauen Pfad aus der Ausgabe notieren.

## Vollständiger Test-Reset – löscht Daten

**Achtung:** Nur für einen bewusst gewünschten vollständigen Reset verwenden. Der folgende Befehl überspringt Rückfragen und kann Nutzerdaten sowie die virtuelle Python-Umgebung unwiederbringlich entfernen:

```bash
sudo mediahub-ai-node-uninstall --purge --remove-venv --yes
```

Dieser Befehl ist **nicht** für ein normales Update erforderlich.

## Ergebnis kontrollieren

```bash
systemctl is-active mediahub-ai-node
systemctl is-enabled mediahub-ai-node
ls -ld /opt/mediahub/ai-node
```

Nach einer vollständigen Deinstallation sollten Dienst und Programmordner nicht mehr vorhanden sein. Ein eventuell gesicherter Datenordner und der Linux-Benutzer können weiterhin existieren.

Siehe auch [Installation](INSTALLATION.md) und [Update](UPDATE.md).
