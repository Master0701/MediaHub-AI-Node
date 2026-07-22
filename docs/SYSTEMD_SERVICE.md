# systemd-Dienst

## Beispiel

```ini
[Unit]
Description=MediaHub AI Node
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=mediahub
Group=mediahub
WorkingDirectory=/opt/mediahub/ai-node
EnvironmentFile=-/opt/mediahub/ai-node/.env
ExecStart=/opt/mediahub/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8765
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Speichern als:

```text
/etc/systemd/system/mediahub-ai-node.service
```

## Aktivieren

```bash
sudo systemctl daemon-reload
sudo systemctl enable mediahub-ai-node
sudo systemctl start mediahub-ai-node
```

## Status und Logs

```bash
sudo systemctl status mediahub-ai-node --no-pager
sudo journalctl -u mediahub-ai-node -n 200 --no-pager
sudo journalctl -u mediahub-ai-node -f
```

## Neustart

```bash
sudo systemctl restart mediahub-ai-node
```

## Aktueller Port

Der bestätigte Dienst läuft auf Port `8765`, nicht auf Port `8000`.
