# systemd-Dienst

Der Dienst wird normalerweise automatisch durch `sudo ./install.sh` eingerichtet.

```ini
[Unit]
Description=MediaHub AI Node
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=<gewählter Linux-Benutzer>
Group=<zugehörige Gruppe>
WorkingDirectory=/opt/mediahub/ai-node
EnvironmentFile=/opt/mediahub/ai-node/.env
ExecStart=/opt/mediahub/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8765
Restart=on-failure
RestartSec=5
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=full
ReadWritePaths=/opt/mediahub/ai-node

[Install]
WantedBy=multi-user.target
```

Standardbenutzer ist `mediahub`, kann aber frei gewählt werden.

Die `.env` enthält unter anderem:

```text
MEDIAHUB_AI_NODE_API_TOKEN=<sicheres Token>
```

Der Installer setzt Eigentümer, Rechte und Modus `600` automatisch.

## Befehle

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now mediahub-ai-node
sudo systemctl status mediahub-ai-node --no-pager
sudo journalctl -u mediahub-ai-node -f
```
