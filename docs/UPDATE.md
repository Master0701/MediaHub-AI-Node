# MediaHub-AI-Node auf dem Raspberry Pi aktualisieren

Diese Anleitung gilt für die mit `install.sh` eingerichtete Raspberry-Pi-Installation unter `/opt/mediahub/ai-node`. **Nicht** einfach `git pull` in diesem Verzeichnis ausführen: Der Installer kopiert die Anwendung ohne `.git` dorthin.

## 1. Vorhandenen Stand prüfen

```bash
sudo systemctl status mediahub-ai-node --no-pager
curl -fsS http://127.0.0.1:8765/health
```

## 2. Sicherung anlegen

Vor jedem Update die Einstellungen und Nutzerdaten sichern. Ein Beispiel für ein lokales, nur für Root lesbares Archiv:

```bash
sudo mkdir -p /opt/mediahub/ai-node-update-backups
sudo chmod 700 /opt/mediahub/ai-node-update-backups
sudo tar -C /opt/mediahub/ai-node -czpf \
  "/opt/mediahub/ai-node-update-backups/pre-update-$(date +%Y%m%d-%H%M%S).tar.gz" \
  .env plugins data backups models
```

Das setzt voraus, dass diese Verzeichnisse existieren. Fehlende Verzeichnisse gegebenenfalls aus der Liste entfernen. Das Archiv enthält unter Umständen API-Schlüssel und private Daten: nicht öffentlich hochladen.

## 3. Neue Version herunterladen

Für den aktuell dokumentierten Weg das GitHub-Repository **in einen separaten Quellordner** holen oder einen vorhandenen Quellklon aktualisieren:

```bash
cd ~
if [ -d MediaHub-AI-Node/.git ]; then
  cd MediaHub-AI-Node
  git pull --ff-only origin main
else
  git clone https://github.com/Master0701/MediaHub-AI-Node.git
  cd MediaHub-AI-Node
fi
```

Dieser Weg installiert den aktuellen `main`-Stand. Für eine bestimmte freigegebene Version stattdessen den gewünschten Git-Tag im **Quellordner** auschecken, nachdem dessen Inhalt und Versionsstand geprüft wurden.

## 4. Update durchführen

```bash
sudo ./install.sh
```

Der Installer kopiert die Anwendung nach `/opt/mediahub/ai-node`, aktualisiert Python-Abhängigkeiten, installiert den Dienst erneut und startet ihn. Das vorhandene API-Token wird aus der bisherigen `.env` übernommen, **die übrigen `.env`-Einträge werden jedoch neu geschrieben**. Deshalb vorab sichern und danach individuelle Einstellungen vergleichen.

**Wichtig:** `install.sh` ist aktuell ein Installationsskript und kein eigens abgesicherter Migrations-Updater. Es kopiert neue Dateien in das bestehende Ziel und löscht vorhandene Dateien nicht grundsätzlich. Vor produktiven Updates mit individuellen Änderungen oder kritischen Daten unbedingt die Sicherung prüfen. Vorhandene Plugin- und Datenordner nicht manuell löschen.

## 5. Funktion nach dem Update prüfen

```bash
sudo systemctl status mediahub-ai-node --no-pager
curl -fsS http://127.0.0.1:8765/health
sudo journalctl -u mediahub-ai-node -n 80 --no-pager
```

Danach im MediaHub-Programm die Node-Verbindung, installierten Plugins, Backup-Liste und die benötigten KI-Funktionen prüfen. Das Update gilt erst als abgeschlossen, wenn diese Prüfungen erfolgreich sind.

## Probleme nach dem Update

Nicht vorschnell `/opt/mediahub/ai-node`, `.env`, `plugins`, `data` oder `backups` löschen. Zuerst die Dienstprotokolle prüfen und das angelegte Sicherungsarchiv aufbewahren. Ein Zurückspielen sollte geplant und bei gestopptem Dienst erfolgen, da die gesicherte Version möglicherweise andere Datenstrukturen verwendet.

Weitere Hinweise: [Installation](INSTALLATION.md), [Backup und Wiederherstellung](BACKUP_AND_RESTORE.md), [Fehlerbehebung](TROUBLESHOOTING.md).
