# Backup und Wiederherstellung

## Backup erstellen

```bash
cd /opt/mediahub/ai-node
./scripts/backup_ai_node.sh
```

Das Skript sichert:

- Projektdateien
- Datenbank und lokale Projektkonfiguration, soweit sie im Projekt liegen
- Python-Abhängigkeitsliste
- Python-Version
- systemd-Dienst und Override
- Dienststatus
- Systeminformationen
- SHA-256-Prüfsumme

Die virtuelle Umgebung wird nicht gesichert. Sie wird nach einer Wiederherstellung sauber neu aufgebaut.

## Prüfsumme kontrollieren

```bash
sha256sum -c \
  /opt/mediahub/ai-node/backups/mediahub-ai-node_*.tar.gz.sha256
```

Ein gültiges Ergebnis endet mit `OK`.

## Externe Sicherung

Mindestens eine Kopie muss außerhalb des Raspberry Pi liegen, etwa auf:

- NAS
- anderem Rechner
- externer SSD
- verschlüsseltem Backup-Speicher

## Wiederherstellung

```bash
cd /opt/mediahub/ai-node
./scripts/restore_ai_node.sh \
  /pfad/zum/mediahub-ai-node_YYYY-MM-DD_HH-MM-SS.tar.gz
```

Danach die virtuelle Umgebung neu erstellen und die im Backup enthaltene `requirements-backup.txt` installieren.

## Notfallablauf

1. Raspberry Pi OS neu installieren.
2. Benutzer `mediahub` und `/opt/mediahub` vorbereiten.
3. Backup und Prüfsumme auf den Pi kopieren.
4. Prüfsumme kontrollieren.
5. Projekt und systemd-Dienst wiederherstellen.
6. virtuelle Umgebung neu erstellen.
7. Abhängigkeiten installieren.
8. Dienst starten.
9. Health-Check ausführen.
10. automatischen Abschlusstest ausführen.
