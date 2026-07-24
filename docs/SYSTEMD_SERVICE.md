# systemd-Dienst

## Dienstdatei erstellen

```bash
sudo nano /etc/systemd/system/mediahub-ai-node.service
```

Beispiel:

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

## Aktivieren

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now mediahub-ai-node
```

## Status und Protokoll

```bash
sudo systemctl status mediahub-ai-node
sudo journalctl -u mediahub-ai-node -f
```
