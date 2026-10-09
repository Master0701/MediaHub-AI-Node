"""Lokale Status-Webseite des MediaHub AI Node."""

from __future__ import annotations

import html
import platform
import socket
from datetime import UTC, datetime

import psutil
from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from app.config import APP_NAME, APP_VERSION
from app.plugins.runtime import node_activity, plugin_manager

router = APIRouter()


def _format_duration(seconds: object) -> str:
    try:
        value = max(0, int(float(seconds)))
    except (TypeError, ValueError):
        return "—"

    minutes, secs = divmod(value, 60)
    hours, minutes = divmod(minutes, 60)

    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"

    return f"{minutes}:{secs:02d}"


def _format_last_seen(seconds: object) -> str:
    if seconds is None:
        return "Noch kein Heartbeat"

    try:
        value = max(0, int(float(seconds)))
    except (TypeError, ValueError):
        return "—"

    if value < 2:
        return "Gerade eben"

    if value < 60:
        return f"Vor {value} Sekunden"

    minutes = value // 60

    if minutes == 1:
        return "Vor 1 Minute"

    if minutes < 60:
        return f"Vor {minutes} Minuten"

    hours = minutes // 60

    if hours == 1:
        return "Vor 1 Stunde"

    return f"Vor {hours} Stunden"


def _plugin_rows() -> str:
    rows: list[str] = []

    for record in plugin_manager.registry.all():
        manifest = record.manifest

        name = html.escape(
            str(
                getattr(manifest, "name", None)
                or getattr(manifest, "plugin_id", "Unbekannt")
            )
        )

        version = html.escape(
            str(getattr(manifest, "version", "—"))
        )

        plugin_id = html.escape(
            str(getattr(manifest, "plugin_id", "—"))
        )

        if record.error:
            state = "Fehler"
        elif record.loaded:
            state = "Bereit"
        elif record.enabled:
            state = "Ruhemodus"
        else:
            state = "Deaktiviert"

        dot_class = (
            "red" if record.error
            else "green" if record.loaded
            else "yellow" if record.enabled
            else "gray"
        )

        rows.append(
            f"""
            <div class="plugin">
                <div>
                    <strong><span class="dot plugin-dot {dot_class}"></span>{name}</strong>
                    <div class="muted">
                        v{version} · {html.escape(state)}
                    </div>
                </div>
                <div class="worker">
                    Plugin: {plugin_id}
                </div>
            </div>
            """
        )

    if not rows:
        return '<div class="empty">Keine Plugins installiert.</div>'

    return "\n".join(rows)


@router.get(
    "/status",
    response_class=HTMLResponse,
    include_in_schema=False,
)
def status_page() -> HTMLResponse:
    activity = node_activity.status()

    sleeping = bool(activity.get("sleeping"))
    connected = bool(activity.get("mediahub_connected"))

    state_title = "Ruhemodus" if sleeping else "Aktiv"
    state_text = (
        "Plugins befinden sich im Ruhemodus"
        if sleeping
        else "AI Node ist betriebsbereit"
    )

    node_dot = "yellow" if sleeping else "green"
    connection_dot = "green" if connected else "red"
    activity_dot = "green" if connected else "gray"

    connection_text = (
        "Verbunden"
        if connected
        else "Nicht verbunden"
    )

    last_seen = _format_last_seen(
        activity.get("mediahub_last_seen_seconds")
    )

    active_jobs = activity.get("active_jobs", 0)

    try:
        jobs_running = int(active_jobs) > 0
    except (TypeError, ValueError):
        jobs_running = False

    jobs_dot = "green" if jobs_running else "gray"
    sleep_dot = "yellow" if sleeping else "green"

    try:
        jobs_running = int(active_jobs) > 0
    except (TypeError, ValueError):
        jobs_running = False

    jobs_dot = "green" if jobs_running else "gray"

    if sleeping:
        sleep_text = "Aktiv"
    else:
        sleep_text = _format_duration(
            activity.get("seconds_until_sleep")
        )

    hostname = socket.gethostname()
    machine = platform.machine() or "—"
    system_name = platform.system() or "Linux"

    memory = psutil.virtual_memory()
    cpu_count = psutil.cpu_count(logical=True) or 0

    generated = datetime.now(UTC).strftime(
        "%Y-%m-%d %H:%M:%S UTC"
    )

    document = f"""<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="refresh" content="5">
<title>{html.escape(APP_NAME)} · Status</title>
<style>
:root {{
    color-scheme: dark;
    font-family:
        Inter, system-ui, -apple-system, BlinkMacSystemFont,
        "Segoe UI", sans-serif;
    background: #0d1117;
    color: #f0f3f6;
}}

* {{
    box-sizing: border-box;
}}

body {{
    margin: 0;
    background:
        radial-gradient(circle at top left, #172033, #0d1117 42%);
    min-height: 100vh;
}}

main {{
    width: min(980px, calc(100% - 32px));
    margin: 40px auto;
}}

header {{
    margin-bottom: 24px;
}}

.brand {{
    font-size: 15px;
    font-weight: 700;
    letter-spacing: .12em;
    color: #8b949e;
    margin-bottom: 8px;
}}

h1 {{
    margin: 0;
    font-size: clamp(28px, 5vw, 46px);
}}

.version {{
    color: #8b949e;
    margin-top: 6px;
}}

.hero {{
    border: 1px solid #30363d;
    background: rgba(22, 27, 34, .92);
    border-radius: 18px;
    padding: 22px;
    margin-bottom: 18px;
}}

.hero-title {{
    font-size: 24px;
    font-weight: 750;
    margin-bottom: 5px;
}}

.muted {{
    color: #8b949e;
}}

.dot {{
    display: inline-block;
    width: 11px;
    height: 11px;
    border-radius: 50%;
    margin-right: 9px;
    vertical-align: middle;
    background: #697687;
    box-shadow: 0 0 0 3px rgba(255, 255, 255, .04);
}}

.dot.green {{ background: #43d17b; }}
.dot.yellow {{ background: #e8bd45; }}
.dot.red {{ background: #ef5b5b; }}
.dot.gray {{ background: #697687; }}

.plugin-dot {{
    width: 10px;
    height: 10px;
}}

.grid {{
    display: grid;
    grid-template-columns:
        repeat(auto-fit, minmax(210px, 1fr));
    gap: 14px;
    margin-bottom: 18px;
}}

.card {{
    border: 1px solid #30363d;
    background: rgba(22, 27, 34, .88);
    border-radius: 15px;
    padding: 17px;
}}

.label {{
    color: #8b949e;
    font-size: 13px;
    margin-bottom: 7px;
}}

.value {{
    font-size: 20px;
    font-weight: 700;
    overflow-wrap: anywhere;
}}

section {{
    border: 1px solid #30363d;
    background: rgba(22, 27, 34, .88);
    border-radius: 18px;
    padding: 20px;
    margin-bottom: 18px;
}}

section h2 {{
    margin: 0 0 15px;
    font-size: 19px;
}}

.plugin {{
    display: flex;
    justify-content: space-between;
    gap: 20px;
    padding: 14px 0;
    border-top: 1px solid #21262d;
}}

.plugin:first-of-type {{
    border-top: 0;
}}

.worker {{
    color: #8b949e;
    text-align: right;
    font-size: 13px;
    overflow-wrap: anywhere;
}}

.empty {{
    color: #8b949e;
}}

footer {{
    color: #6e7681;
    text-align: center;
    font-size: 12px;
    padding: 6px;
}}

@media (max-width: 600px) {{
    main {{
        margin: 22px auto;
    }}

    .plugin {{
        display: block;
    }}

    .worker {{
        text-align: left;
        margin-top: 7px;
    }}
}}
</style>
</head>
<body>
<main>
<header>
    <div class="brand">M</div>
    <h1>MediaHub AI Node</h1>
    <div class="version">Version {html.escape(APP_VERSION)}</div>
</header>

<div class="hero">
    <div class="hero-title"><span class="dot {node_dot}"></span>{html.escape(state_title)}</div>
    <div class="muted">{html.escape(state_text)}</div>
</div>

<div class="grid">
    <div class="card">
        <div class="label">MediaHub</div>
        <div class="value">
        <span class="dot {connection_dot}"></span>
        {html.escape(connection_text)}
    </div>
    </div>

    <div class="card">
        <div class="label">Letzte Aktivität</div>
        <div class="value"><span class="dot {activity_dot}"></span>{html.escape(last_seen)}</div>
    </div>

    <div class="card">
        <div class="label">Aktive Jobs</div>
        <div class="value"><span class="dot {jobs_dot}"></span>{html.escape(str(active_jobs))}</div>
    </div>

    <div class="card">
        <div class="label">Ruhemodus</div>
        <div class="value"><span class="dot {sleep_dot}"></span>{html.escape(sleep_text)}</div>
    </div>

    <div class="card">
        <div class="label">Hostname</div>
        <div class="value">{html.escape(hostname)}</div>
    </div>

    <div class="card">
        <div class="label">Plattform</div>
        <div class="value">
            {html.escape(system_name)} ({html.escape(machine)})
        </div>
    </div>

    <div class="card">
        <div class="label">CPU</div>
        <div class="value">{cpu_count} Threads</div>
    </div>

    <div class="card">
        <div class="label">Arbeitsspeicher</div>
        <div class="value">
            {memory.percent:.1f}% verwendet
        </div>
    </div>
</div>

<section>
    <h2>Installierte Plugins</h2>
    {_plugin_rows()}
</section>

<footer>
    Lokale Statusseite · API-Token wird nicht angezeigt ·
    {html.escape(generated)}
</footer>
</main>
</body>
</html>
"""

    return HTMLResponse(document)
