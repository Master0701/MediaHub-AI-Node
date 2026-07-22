#!/usr/bin/env bash

set -uo pipefail

SERVICE_NAME="${SERVICE_NAME:-mediahub-ai-node}"
PROJECT_DIR="${PROJECT_DIR:-/opt/mediahub/ai-node}"
VENV_DIR="${VENV_DIR:-/opt/mediahub/venv}"
API_URL="${API_URL:-http://127.0.0.1:8765}"
MIN_FREE_GB="${MIN_FREE_GB:-10}"
MAX_MEMORY_PERCENT="${MAX_MEMORY_PERCENT:-90}"
MAX_TEMPERATURE_C="${MAX_TEMPERATURE_C:-80}"
RUN_SMOKE_TEST="${RUN_SMOKE_TEST:-0}"

failures=0
warnings=0

ok() {
    printf '✔ %s\n' "$1"
}

warn() {
    printf '⚠ %s\n' "$1"
    warnings=$((warnings + 1))
}

fail() {
    printf '✘ %s\n' "$1"
    failures=$((failures + 1))
}

echo
echo "MediaHub-AI-Node Wartungsprüfung"
echo "================================"
echo

if systemctl is-active --quiet "$SERVICE_NAME"; then
    ok "Dienst aktiv"
else
    fail "Dienst nicht aktiv: $SERVICE_NAME"
fi

health_json="$(curl -fsS --max-time 5 "$API_URL/health" 2>/dev/null || true)"

if [[ -n "$health_json" ]]; then
    ok "REST-API erreichbar"
else
    fail "REST-API nicht erreichbar: $API_URL/health"
fi

if curl -fsS --max-time 5 "$API_URL/openapi.json" >/dev/null 2>&1; then
    ok "OpenAPI erreichbar"
else
    fail "OpenAPI nicht erreichbar"
fi

if [[ -x "$VENV_DIR/bin/python" ]]; then
    python_version="$("$VENV_DIR/bin/python" --version 2>&1)"
    ok "Virtuelle Umgebung vorhanden: $python_version"
else
    fail "Virtuelle Umgebung fehlt: $VENV_DIR"
fi

if [[ -d "$PROJECT_DIR" ]]; then
    ok "Projektordner vorhanden"
else
    fail "Projektordner fehlt: $PROJECT_DIR"
fi

free_gb="$(df -Pk "$PROJECT_DIR" 2>/dev/null | awk 'NR==2 {printf "%.1f", $4/1024/1024}')"
if [[ -n "$free_gb" ]]; then
    if awk -v free="$free_gb" -v min="$MIN_FREE_GB" 'BEGIN {exit !(free >= min)}'; then
        ok "SSD frei: ${free_gb} GB"
    else
        fail "SSD-Speicher knapp: ${free_gb} GB frei"
    fi
else
    warn "Freier SSD-Speicher konnte nicht gelesen werden"
fi

memory_percent="$(free | awk '/Mem:/ {printf "%.1f", $3/$2*100}')"
if [[ -n "$memory_percent" ]]; then
    if awk -v used="$memory_percent" -v max="$MAX_MEMORY_PERCENT" 'BEGIN {exit !(used <= max)}'; then
        ok "RAM-Auslastung: ${memory_percent} %"
    else
        fail "RAM-Auslastung zu hoch: ${memory_percent} %"
    fi
else
    warn "RAM-Auslastung konnte nicht gelesen werden"
fi

temperature=""
if command -v vcgencmd >/dev/null 2>&1; then
    temperature="$(vcgencmd measure_temp 2>/dev/null | sed -E "s/[^0-9.]//g")"
elif [[ -r /sys/class/thermal/thermal_zone0/temp ]]; then
    temperature="$(awk '{printf "%.1f", $1/1000}' /sys/class/thermal/thermal_zone0/temp)"
fi

if [[ -n "$temperature" ]]; then
    if awk -v temp="$temperature" -v max="$MAX_TEMPERATURE_C" 'BEGIN {exit !(temp <= max)}'; then
        ok "CPU-Temperatur: ${temperature} °C"
    else
        fail "CPU-Temperatur zu hoch: ${temperature} °C"
    fi
else
    warn "CPU-Temperatur konnte nicht gelesen werden"
fi

if [[ "$RUN_SMOKE_TEST" == "1" ]]; then
    if [[ -f "$PROJECT_DIR/tests/test_ai_node_smoke.py" && -x "$VENV_DIR/bin/python" ]]; then
        if (
            cd "$PROJECT_DIR" &&
            PYTHONPATH=. "$VENV_DIR/bin/python" tests/test_ai_node_smoke.py
        ); then
            ok "Smoke-Test erfolgreich"
        else
            fail "Smoke-Test fehlgeschlagen"
        fi
    else
        warn "Smoke-Test nicht gefunden oder Python fehlt"
    fi
fi

echo
echo "--------------------------------"
if [[ "$failures" -eq 0 ]]; then
    if [[ "$warnings" -eq 0 ]]; then
        echo "Gesamtstatus: OK"
    else
        echo "Gesamtstatus: OK mit ${warnings} Warnung(en)"
    fi
    exit 0
fi

echo "Gesamtstatus: FEHLER (${failures} Fehler, ${warnings} Warnungen)"
exit 1
