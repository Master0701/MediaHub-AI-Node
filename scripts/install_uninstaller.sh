#!/usr/bin/env bash

set -Eeuo pipefail

PROJECT_DIR="${PROJECT_DIR:-/opt/mediahub/ai-node}"
SOURCE_FILE="${PROJECT_DIR}/uninstall.sh"
TARGET_FILE="/usr/local/sbin/mediahub-ai-node-uninstall"

if [[ "${EUID}" -ne 0 ]]; then
    echo "Bitte mit sudo ausführen." >&2
    exit 1
fi

if [[ ! -f "$SOURCE_FILE" ]]; then
    echo "Uninstaller fehlt: $SOURCE_FILE" >&2
    exit 1
fi

install -o root -g root -m 0755 "$SOURCE_FILE" "$TARGET_FILE"

echo "Systemweiter Uninstaller installiert:"
echo "$TARGET_FILE"
