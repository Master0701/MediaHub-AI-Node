#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
DEFAULT_USER="mediahub"
PROJECT_DIR="${PROJECT_DIR:-/opt/mediahub/ai-node}"
VENV_DIR="${VENV_DIR:-/opt/mediahub/venv}"
SERVICE_NAME="${SERVICE_NAME:-mediahub-ai-node}"
API_PORT="${MEDIAHUB_AI_PORT:-8765}"
MEDIAHUB_USER="${MEDIAHUB_USER:-}"
MEDIAHUB_GROUP="${MEDIAHUB_GROUP:-}"
NONINTERACTIVE="${MEDIAHUB_NONINTERACTIVE:-0}"

log() { printf '[MediaHub-AI-Node] %s\n' "$*"; }
fail() { printf '[MediaHub-AI-Node] FEHLER: %s\n' "$*" >&2; exit 1; }

[[ ${EUID} -eq 0 ]] || fail "Bitte mit sudo oder als root ausführen."

if [[ -z "$MEDIAHUB_USER" ]]; then
    if [[ "$NONINTERACTIVE" == "1" ]]; then
        MEDIAHUB_USER="$DEFAULT_USER"
    else
        read -r -p "Linux-Benutzer für den AI-Node [$DEFAULT_USER]: " answer
        MEDIAHUB_USER="${answer:-$DEFAULT_USER}"
    fi
fi

if ! id -u "$MEDIAHUB_USER" >/dev/null 2>&1; then
    if [[ "$NONINTERACTIVE" == "1" ]]; then
        useradd --create-home --shell /bin/bash "$MEDIAHUB_USER"
    else
        read -r -p "Benutzer '$MEDIAHUB_USER' anlegen? [J/n]: " answer
        case "${answer:-J}" in
            J|j|Y|y) useradd --create-home --shell /bin/bash "$MEDIAHUB_USER" ;;
            *) fail "Benutzer existiert nicht." ;;
        esac
    fi
fi

MEDIAHUB_GROUP="${MEDIAHUB_GROUP:-$(id -gn "$MEDIAHUB_USER")}"

export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y python3 python3-venv python3-pip curl ca-certificates git

mkdir -p "$PROJECT_DIR"
if [[ "$(readlink -f "$SCRIPT_DIR")" != "$(readlink -f "$PROJECT_DIR")" ]]; then
    tar --exclude='.git' --exclude='.venv' --exclude='venv'         --exclude='__pycache__' --exclude='.pytest_cache'         --exclude='.ruff_cache' -C "$SCRIPT_DIR" -cf - . |
        tar -C "$PROJECT_DIR" -xf -
fi

mkdir -p     "$PROJECT_DIR/plugins"     "$PROJECT_DIR/data/plugin_plans"     "$PROJECT_DIR/backups/plugins"     "$PROJECT_DIR/cache"     "$PROJECT_DIR/jobs"     "$PROJECT_DIR/logs"     "$PROJECT_DIR/models"

if [[ ! -x "$VENV_DIR/bin/python" ]]; then
    python3 -m venv "$VENV_DIR"
fi
"$VENV_DIR/bin/python" -m pip install --upgrade pip
"$VENV_DIR/bin/python" -m pip install -r "$PROJECT_DIR/requirements.txt"

TOKEN=""
if [[ -f "$PROJECT_DIR/.env" ]]; then
    TOKEN="$(sed -n 's/^MEDIAHUB_AI_NODE_API_TOKEN=\(.*\)$/\1/p' "$PROJECT_DIR/.env" | tail -n 1)"
fi
if [[ -z "$TOKEN" ]]; then
    TOKEN="$("$VENV_DIR/bin/python" -c 'import secrets; print(secrets.token_urlsafe(48))')"
fi

cat > "$PROJECT_DIR/.env" <<EOF
MEDIAHUB_AI_HOST=0.0.0.0
MEDIAHUB_AI_PORT=${API_PORT}
MEDIAHUB_AI_LOG_LEVEL=INFO
MEDIAHUB_AI_DATABASE_DIR=${PROJECT_DIR}/data
MEDIAHUB_AI_CACHE_DIR=${PROJECT_DIR}/cache
MEDIAHUB_AI_JOBS_DIR=${PROJECT_DIR}/jobs
MEDIAHUB_AI_LOG_DIR=${PROJECT_DIR}/logs
MEDIAHUB_AI_MODELS_DIR=${PROJECT_DIR}/models
MEDIAHUB_AI_NODE_API_TOKEN=${TOKEN}
EOF

chown -R "$MEDIAHUB_USER:$MEDIAHUB_GROUP" "$PROJECT_DIR" "$VENV_DIR"
chmod 600 "$PROJECT_DIR/.env"
chmod 750 "$PROJECT_DIR" "$PROJECT_DIR/plugins" "$PROJECT_DIR/data"     "$PROJECT_DIR/data/plugin_plans" "$PROJECT_DIR/backups"     "$PROJECT_DIR/backups/plugins" "$PROJECT_DIR/cache"     "$PROJECT_DIR/jobs" "$PROJECT_DIR/logs" "$PROJECT_DIR/models"
chmod +x "$PROJECT_DIR/install.sh" "$PROJECT_DIR/scripts/"*.sh 2>/dev/null || true

MEDIAHUB_USER="$MEDIAHUB_USER" MEDIAHUB_GROUP="$MEDIAHUB_GROUP" PROJECT_DIR="$PROJECT_DIR" VENV_DIR="$VENV_DIR" SERVICE_NAME="$SERVICE_NAME" API_PORT="$API_PORT"     "$PROJECT_DIR/scripts/install_service.sh"


PROJECT_DIR="$PROJECT_DIR" "$PROJECT_DIR/scripts/install_uninstaller.sh"
for _ in $(seq 1 30); do
    curl -fsS "http://127.0.0.1:${API_PORT}/health" >/dev/null 2>&1 && break
    sleep 1
done

curl -fsS     -H "Authorization: Bearer ${TOKEN}"     "http://127.0.0.1:${API_PORT}/plugins" >/dev/null

printf '\nInstallation erfolgreich.\n'
printf 'MEDIAHUB_AI_NODE_HOST=%s\n' "$(hostname -I 2>/dev/null | awk '{print $1}')"
printf 'MEDIAHUB_AI_NODE_PORT=%s\n' "$API_PORT"
printf 'MEDIAHUB_AI_NODE_USER=%s\n' "$MEDIAHUB_USER"
printf 'MEDIAHUB_AI_NODE_API_TOKEN=%s\n' "$TOKEN"
