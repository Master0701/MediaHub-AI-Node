#!/usr/bin/env bash

set -Eeuo pipefail

PROJECT_DIR="/opt/mediahub/ai-node"
BACKUP_DIR="${PROJECT_DIR}/backups"
SERVICE_NAME="mediahub-ai-node"

TIMESTAMP="$(date '+%Y-%m-%d_%H-%M-%S')"
BACKUP_NAME="mediahub-ai-node_${TIMESTAMP}"
WORK_DIR="${BACKUP_DIR}/${BACKUP_NAME}"
ARCHIVE_FILE="${BACKUP_DIR}/${BACKUP_NAME}.tar.gz"

echo
echo "MediaHub-KI-Knoten Backup"
echo "========================="
echo

if [[ ! -d "${PROJECT_DIR}" ]]; then
    echo "FEHLER: Projektordner nicht gefunden:"
    echo "${PROJECT_DIR}"
    exit 1
fi

mkdir -p "${WORK_DIR}"

echo "[1/6] Dienststatus erfassen ..."

if systemctl is-active --quiet "${SERVICE_NAME}"; then
    SERVICE_WAS_RUNNING="yes"
else
    SERVICE_WAS_RUNNING="no"
fi

systemctl status "${SERVICE_NAME}" \
    --no-pager \
    > "${WORK_DIR}/service-status.txt" \
    2>&1 || true

echo "[2/6] Projektdateien sichern ..."

tar \
    --exclude="./backups" \
    --exclude="./venv" \
    --exclude="./__pycache__" \
    --exclude="*.pyc" \
    -czf "${WORK_DIR}/project.tar.gz" \
    -C "${PROJECT_DIR}" \
    .

echo "[3/6] Systemd-Dienst sichern ..."

if [[ -f "/etc/systemd/system/${SERVICE_NAME}.service" ]]; then
    sudo cp \
        "/etc/systemd/system/${SERVICE_NAME}.service" \
        "${WORK_DIR}/"

    sudo chown \
        "$(id -u):$(id -g)" \
        "${WORK_DIR}/${SERVICE_NAME}.service"
fi

if [[ -d "/etc/systemd/system/${SERVICE_NAME}.service.d" ]]; then
    sudo cp -a \
        "/etc/systemd/system/${SERVICE_NAME}.service.d" \
        "${WORK_DIR}/"

    sudo chown -R \
        "$(id -u):$(id -g)" \
        "${WORK_DIR}/${SERVICE_NAME}.service.d"
fi

echo "[4/6] Python-Abhängigkeiten sichern ..."

python -m pip freeze \
    > "${WORK_DIR}/requirements-backup.txt"

python --version \
    > "${WORK_DIR}/python-version.txt" \
    2>&1

echo "[5/6] Systeminformationen sichern ..."

{
    echo "Backup erstellt:"
    date --iso-8601=seconds

    echo
    echo "Hostname:"
    hostname

    echo
    echo "Betriebssystem:"
    cat /etc/os-release

    echo
    echo "Architektur:"
    uname -m

    echo
    echo "Kernel:"
    uname -a

    echo
    echo "Dienst lief beim Backup:"
    echo "${SERVICE_WAS_RUNNING}"

    echo
    echo "Projektordner:"
    echo "${PROJECT_DIR}"
} > "${WORK_DIR}/system-info.txt"

echo "[6/6] Gesamtarchiv erstellen ..."

tar \
    -czf "${ARCHIVE_FILE}" \
    -C "${BACKUP_DIR}" \
    "${BACKUP_NAME}"

sha256sum "${ARCHIVE_FILE}" \
    > "${ARCHIVE_FILE}.sha256"

rm -rf "${WORK_DIR}"

echo
echo "Backup erfolgreich erstellt:"
echo "${ARCHIVE_FILE}"
echo
echo "Prüfsumme:"
cat "${ARCHIVE_FILE}.sha256"
echo
