#!/usr/bin/env bash
set -Eeuo pipefail

PROJECT_DIR="${PROJECT_DIR:-/opt/mediahub/ai-node}"
VENV_DIR="${VENV_DIR:-/opt/mediahub/venv}"
SERVICE_NAME="${SERVICE_NAME:-mediahub-ai-node}"
MEDIAHUB_USER="${MEDIAHUB_USER:-mediahub}"
MEDIAHUB_GROUP="${MEDIAHUB_GROUP:-$MEDIAHUB_USER}"
API_PORT="${API_PORT:-8765}"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"

[[ ${EUID} -eq 0 ]] || { echo "Bitte mit sudo ausführen." >&2; exit 1; }
id -u "$MEDIAHUB_USER" >/dev/null 2>&1 || { echo "Benutzer fehlt." >&2; exit 1; }
[[ -x "$VENV_DIR/bin/uvicorn" ]] || { echo "Uvicorn fehlt." >&2; exit 1; }
[[ -f "$PROJECT_DIR/.env" ]] || { echo ".env fehlt." >&2; exit 1; }

cat > "$SERVICE_FILE" <<EOF
[Unit]
Description=MediaHub AI Node
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=${MEDIAHUB_USER}
Group=${MEDIAHUB_GROUP}
WorkingDirectory=${PROJECT_DIR}
EnvironmentFile=${PROJECT_DIR}/.env
ExecStart=${VENV_DIR}/bin/uvicorn app.main:app --host 0.0.0.0 --port ${API_PORT}
Restart=on-failure
RestartSec=5
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=full
ReadWritePaths=${PROJECT_DIR}

[Install]
WantedBy=multi-user.target
EOF

chmod 644 "$SERVICE_FILE"
systemctl daemon-reload
systemctl enable "$SERVICE_NAME"
systemctl restart "$SERVICE_NAME"
systemctl status "$SERVICE_NAME" --no-pager
