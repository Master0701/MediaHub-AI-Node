#!/usr/bin/env bash

set -Eeuo pipefail

PROJECT_DIR="/opt/mediahub/ai-node"
SERVICE_NAME="mediahub-ai-node"

if [[ $# -ne 1 ]]; then
    echo
    echo "Verwendung:"
    echo
    echo "  ./restore_ai_node.sh <backup.tar.gz>"
    echo
    exit 1
fi

BACKUP="$1"

if [[ ! -f "$BACKUP" ]]; then
    echo "Backup nicht gefunden:"
    echo "$BACKUP"
    exit 1
fi

TMPDIR="$(mktemp -d)"

cleanup() {
    rm -rf "$TMPDIR"
}

trap cleanup EXIT

echo
echo "MediaHub-KI-Knoten Wiederherstellung"
echo "===================================="
echo

echo "[1/8] Dienst stoppen ..."

sudo systemctl stop "$SERVICE_NAME" || true

echo "[2/8] Backup entpacken ..."

tar -xzf "$BACKUP" -C "$TMPDIR"

ROOT="$(find "$TMPDIR" -mindepth 1 -maxdepth 1 -type d | head -n1)"

echo "[3/8] Projekt löschen ..."

sudo rm -rf "$PROJECT_DIR"

sudo mkdir -p "$PROJECT_DIR"

echo "[4/8] Projekt wiederherstellen ..."

sudo tar \
    -xzf "$ROOT/project.tar.gz" \
    -C "$PROJECT_DIR"

sudo chown -R mediahub:mediahub "$PROJECT_DIR"

echo "[5/8] Systemd-Dienst wiederherstellen ..."

if [[ -f "$ROOT/mediahub-ai-node.service" ]]; then

    sudo cp \
        "$ROOT/mediahub-ai-node.service" \
        /etc/systemd/system/

fi

if [[ -d "$ROOT/mediahub-ai-node.service.d" ]]; then

    sudo mkdir -p \
        /etc/systemd/system/mediahub-ai-node.service.d

    sudo cp -a \
        "$ROOT/mediahub-ai-node.service.d/." \
        /etc/systemd/system/mediahub-ai-node.service.d/

fi

echo "[6/8] systemd aktualisieren ..."

sudo systemctl daemon-reload

echo "[7/8] Python-Hinweis"

echo
echo "Virtuelle Umgebung anschließend neu erstellen:"
echo

echo "python3 -m venv /opt/mediahub/venv"

echo "source /opt/mediahub/venv/bin/activate"

echo "pip install -r $ROOT/requirements-backup.txt"

echo

echo "[8/8] Dienst starten"

echo

echo "sudo systemctl start $SERVICE_NAME"

echo

echo "Wiederherstellung abgeschlossen."
