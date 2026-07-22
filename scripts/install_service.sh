#!/usr/bin/env bash

set -Eeuo pipefail

PROJECT_DIR="${PROJECT_DIR:-/opt/mediahub/ai-node}"
VENV_DIR="${VENV_DIR:-/opt/mediahub/venv}"
SERVICE_NAME="${SERVICE_NAME:-mediahub-ai-node}"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"

if [[ $EUID -ne 0 ]]; then
    echo "Bitte mit sudo ausführen."
    exit 1
fi

cat > "$SERVICE_FILE" <<EOF
[Unit]
Description=MediaHub AI Node
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=mediahub
Group=mediahub
WorkingDirectory=${PROJECT_DIR}
EnvironmentFile=-${PROJECT_DIR}/.env
ExecStart=${VENV_DIR}/bin/uvicorn app.main:app --host 0.0.0.0 --port 8765
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable "$SERVICE_NAME"
systemctl restart "$SERVICE_NAME"
systemctl status "$SERVICE_NAME" --no-pager
