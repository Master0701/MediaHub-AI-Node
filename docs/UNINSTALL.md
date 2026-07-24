# Deinstallation

## Dienst stoppen und deaktivieren

```bash
sudo systemctl stop mediahub-ai-node
sudo systemctl disable mediahub-ai-node
```

## Dienstdatei entfernen

```bash
sudo rm -f /etc/systemd/system/mediahub-ai-node.service
sudo systemctl daemon-reload
```

## Programmdateien entfernen

Vorher bei Bedarf Datenbank, Konfiguration und Backups sichern.

```bash
sudo rm -rf /opt/mediahub/ai-node
```

Die gemeinsam verwendete virtuelle Umgebung `/opt/mediahub/venv` nur löschen,
wenn sie von keiner anderen MediaHub-Komponente mehr verwendet wird.
