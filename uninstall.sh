#!/usr/bin/env bash

set -Eeuo pipefail

SERVICE_NAME="${SERVICE_NAME:-mediahub-ai-node}"
PROJECT_DIR="${PROJECT_DIR:-/opt/mediahub/ai-node}"
VENV_DIR="${VENV_DIR:-/opt/mediahub/venv}"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
DROPIN_DIR="/etc/systemd/system/${SERVICE_NAME}.service.d"
SYSTEM_COMMAND="/usr/local/sbin/mediahub-ai-node-uninstall"

PURGE=0
REMOVE_VENV=0
ASSUME_YES=0
PRESERVE_DIR=""

usage() {
    cat <<'EOF'
MediaHub-AI-Node deinstallieren

Verwendung:
  sudo mediahub-ai-node-uninstall [Optionen]

Optionen:
  --purge          Projekt, Daten, Cache, Modelle und Backups vollständig löschen
  --remove-venv    Gemeinsame Python-Umgebung /opt/mediahub/venv löschen
  --yes            Rückfragen automatisch bestätigen
  --help           Diese Hilfe anzeigen

Beispiele:
  sudo mediahub-ai-node-uninstall
  sudo mediahub-ai-node-uninstall --purge --remove-venv --yes
EOF
}

log() {
    printf '[MediaHub-AI-Node] %s\n' "$*"
}

confirm() {
    local prompt="$1"

    if [[ "$ASSUME_YES" -eq 1 ]]; then
        return 0
    fi

    local answer
    read -r -p "${prompt} [j/N]: " answer
    case "$answer" in
        j|J|y|Y|ja|JA|yes|YES) return 0 ;;
        *) return 1 ;;
    esac
}

require_root() {
    if [[ "${EUID}" -ne 0 ]]; then
        echo "Bitte mit sudo ausführen." >&2
        exit 1
    fi
}

parse_arguments() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --purge)
                PURGE=1
                ;;
            --remove-venv)
                REMOVE_VENV=1
                ;;
            --yes|-y)
                ASSUME_YES=1
                ;;
            --help|-h)
                usage
                exit 0
                ;;
            *)
                echo "Unbekannte Option: $1" >&2
                usage >&2
                exit 2
                ;;
        esac
        shift
    done
}

stop_and_remove_service() {
    log "Dienst wird gestoppt und deaktiviert ..."

    systemctl disable --now "$SERVICE_NAME" >/dev/null 2>&1 || true
    rm -f "$SERVICE_FILE"
    rm -rf "$DROPIN_DIR"

    systemctl daemon-reload
    systemctl reset-failed "$SERVICE_NAME" >/dev/null 2>&1 || true
}

preserve_user_data() {
    local timestamp
    timestamp="$(date +%Y%m%d-%H%M%S)"
    PRESERVE_DIR="/opt/mediahub/ai-node-preserved-${timestamp}"

    mkdir -p "$PRESERVE_DIR"

    local item
    for item in data backups models; do
        if [[ -e "${PROJECT_DIR}/${item}" ]]; then
            mv "${PROJECT_DIR}/${item}" "$PRESERVE_DIR/"
        fi
    done

    if [[ -f "${PROJECT_DIR}/.env" ]]; then
        cp -a "${PROJECT_DIR}/.env" "$PRESERVE_DIR/.env"
        chmod 600 "$PRESERVE_DIR/.env"
    fi

    log "Daten wurden gesichert unter: ${PRESERVE_DIR}"
}

remove_project() {
    if [[ ! -d "$PROJECT_DIR" ]]; then
        log "Projektordner ist bereits entfernt."
        return
    fi

    if [[ "$PURGE" -eq 1 ]]; then
        log "Projektordner einschließlich Daten wird vollständig entfernt ..."
    else
        if confirm "Daten, Modelle und Backups vor dem Entfernen behalten?"; then
            preserve_user_data
        fi
        log "Projektordner wird entfernt ..."
    fi

    rm -rf "$PROJECT_DIR"
}

remove_virtual_environment() {
    if [[ "$REMOVE_VENV" -ne 1 ]]; then
        log "Python-Umgebung bleibt erhalten: ${VENV_DIR}"
        return
    fi

    if [[ -d "$VENV_DIR" ]]; then
        log "Python-Umgebung wird entfernt: ${VENV_DIR}"
        rm -rf "$VENV_DIR"
    else
        log "Python-Umgebung ist bereits entfernt."
    fi
}

verify_removal() {
    local failed=0

    if systemctl list-unit-files "$SERVICE_NAME.service" 2>/dev/null |
        grep -q "^${SERVICE_NAME}.service"; then
        echo "WARNUNG: Dienstdatei ist noch registriert." >&2
        failed=1
    fi

    if [[ -e "$PROJECT_DIR" ]]; then
        echo "WARNUNG: Projektordner existiert noch: $PROJECT_DIR" >&2
        failed=1
    fi

    if command -v ss >/dev/null 2>&1 &&
        ss -ltn 2>/dev/null |
        grep -qE '(^|[[:space:]])[^[:space:]]*:8765[[:space:]]'; then
        echo "WARNUNG: Port 8765 wird weiterhin verwendet." >&2
        failed=1
    fi

    if [[ "$failed" -eq 0 ]]; then
        log "Deinstallation erfolgreich abgeschlossen."
    else
        echo "Deinstallation abgeschlossen, aber die Prüfungen meldeten Warnungen." >&2
        return 1
    fi
}

remove_system_command() {
    if [[ -f "$SYSTEM_COMMAND" ]]; then
        rm -f "$SYSTEM_COMMAND"
    fi
}

main() {
    require_root
    parse_arguments "$@"

    echo
    echo "MediaHub-AI-Node wird deinstalliert."
    echo "Linux-Benutzer und dessen persönliches Home-Verzeichnis werden nicht gelöscht."
    echo

    if [[ "$PURGE" -eq 1 ]]; then
        log "Vollständiger Löschmodus ist aktiviert."
    elif ! confirm "MediaHub-AI-Node jetzt deinstallieren?"; then
        log "Abgebrochen."
        exit 0
    fi

    stop_and_remove_service
    remove_project
    remove_virtual_environment
    verify_removal

    log "Der systemweite Uninstaller wird entfernt."
    remove_system_command
}

main "$@"
