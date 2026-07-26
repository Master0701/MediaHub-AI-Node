# MediaHub-AI-Node deinstallieren

Der Uninstaller ist Bestandteil des GitHub-Repositories und wird bei der
Installation zusätzlich systemweit eingerichtet:

```text
/usr/local/sbin/mediahub-ai-node-uninstall
```

Dadurch kann er den Projektordner und die virtuelle Python-Umgebung entfernen,
ohne sich selbst vorher zu löschen.

## Normale Deinstallation

```bash
sudo mediahub-ai-node-uninstall
```

Der Uninstaller:

- stoppt und deaktiviert den systemd-Dienst,
- entfernt Dienstdatei und Drop-ins,
- führt `systemctl daemon-reload` aus,
- entfernt `/opt/mediahub/ai-node`,
- kann Daten, Modelle und Backups vorher sichern,
- lässt `/opt/mediahub/venv` standardmäßig bestehen,
- löscht den verwendeten Linux-Benutzer nicht,
- prüft am Ende Dienst, Projektordner und Port 8765.

## Vollständiger Test-Reset

Für einen neuen automatischen Installationstest:

```bash
sudo mediahub-ai-node-uninstall --purge --remove-venv --yes
```

Dabei werden entfernt:

```text
/etc/systemd/system/mediahub-ai-node.service
/etc/systemd/system/mediahub-ai-node.service.d/
/opt/mediahub/ai-node
/opt/mediahub/venv
/usr/local/sbin/mediahub-ai-node-uninstall
```

Der Linux-Benutzer bleibt erhalten.

## Daten behalten

Ohne `--purge` fragt der Uninstaller, ob folgende Inhalte gesichert werden
sollen:

```text
data/
backups/
models/
.env
```

Die Sicherung wird unter einem Zeitstempelordner abgelegt:

```text
/opt/mediahub/ai-node-preserved-YYYYMMDD-HHMMSS
```
