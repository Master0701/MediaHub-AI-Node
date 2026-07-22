# Fehlerbehebung

## `ModuleNotFoundError: No module named 'app'`

Im Projektordner starten:

```bash
cd /opt/mediahub/ai-node
PYTHONPATH=. python tests/test_ai_node_smoke.py
```

Der Test sollte den Projektordner selbst in `sys.path` einfügen.

## API nicht erreichbar

```bash
systemctl is-active mediahub-ai-node
ss -ltnp | grep 8765
curl -v http://127.0.0.1:8765/health
```

Der aktuelle Port ist `8765`.

## Dienst startet nicht

```bash
sudo systemctl status mediahub-ai-node --no-pager
sudo journalctl -u mediahub-ai-node -n 200 --no-pager
```

## Port belegt

```bash
sudo ss -ltnp | grep 8765
```

Den fremden Dienst nicht blind beenden. Zuerst Prozess und Ursache bestimmen.

## Datenbankfehler

- Schreibrechte im Datenordner prüfen.
- Datenbankdatei sichern.
- Logs lesen.
- Migrationen nicht mehrfach oder ungeprüft ausführen.
- Bei Beschädigung nur ein geprüftes Backup verwenden.

## Backup beschädigt

```bash
sha256sum -c backup.tar.gz.sha256
```

Bei Fehlern das Archiv nicht wiederherstellen.

## Berechtigungsfehler beim Backup

Mit `sudo` kopierte systemd-Dateien können `root` gehören. Das Backup-Skript muss diese Dateien vor dem Aufräumen mit `chown` an den ausführenden Benutzer übergeben.

## `httpx2`-Warnung

Die beobachtete Starlette-Warnung ist eine Abkündigungswarnung. Sie ist kein Testfehler, solange der Test erfolgreich endet. Abhängigkeiten später kontrolliert und gemeinsam aktualisieren.
