"""Read-only inspection of the dedicated Windows HTTPS firewall rule.

Never changes firewall settings. A rule with the expected name but unexpected
properties is reported as a mismatch, not as permission to create another rule.
"""
from __future__ import annotations

import json
import subprocess
import sys

RULE_NAME = "MediaHub Interaktions-KI HTTPS LAN"


def firewall_status(host: str, port: int = 8769) -> dict:
    result = {"configured": False, "rule": RULE_NAME, "host": host, "port": port,
              "exists": False, "reason": "Firewall-Status nicht verfuegbar"}
    if sys.platform != "win32":
        result["reason"] = "Nur unter Windows verfuegbar"
        return result

    # No interpolated user input. PowerShell emits simple scalar strings;
    # Python performs the comparisons to avoid PowerShell enum/bitmask quirks.
    script = (
        "$ErrorActionPreference='Stop'; "
        "[Console]::OutputEncoding=New-Object System.Text.UTF8Encoding($false); "
        "$items=@(Get-NetFirewallRule -DisplayName 'MediaHub Interaktions-KI HTTPS LAN' "
        "-ErrorAction SilentlyContinue | ForEach-Object { "
        "$r=$_; $p=$r | Get-NetFirewallPortFilter; $a=$r | Get-NetFirewallAddressFilter; "
        "[pscustomobject]@{enabled=[string]$r.Enabled;direction=[string]$r.Direction;"
        "action=[string]$r.Action;profile=[string]$r.Profile;"
        "protocol=[string]$p.Protocol;port=[string]$p.LocalPort;"
        "local=[string]$a.LocalAddress;remote=[string]$a.RemoteAddress} }); "
        "ConvertTo-Json -InputObject $items -Compress -Depth 4"
    )
    try:
        proc = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
            capture_output=True, text=False, timeout=15, creationflags=0x08000000,
        )
        if proc.returncode != 0:
            result["reason"] = "Firewall-Abfrage fehlgeschlagen"
            return result
        raw = proc.stdout.decode("utf-8-sig", errors="replace").strip()
        data = json.loads(raw) if raw else []
        entries = data if isinstance(data, list) else ([data] if isinstance(data, dict) else [])
        result["exists"] = bool(entries)
        for entry in entries:
            profiles = str(entry.get("profile", "")).lower().replace(" ", "")
            private_profile = "private" in profiles.split(",") or "2" in profiles.split(",")
            if (str(entry.get("enabled", "")).lower() == "true"
                and str(entry.get("direction", "")).lower() == "inbound"
                and str(entry.get("action", "")).lower() == "allow"
                and private_profile
                and str(entry.get("protocol", "")).lower() in ("tcp", "6")
                and str(entry.get("port", "")) == str(port)
                and str(entry.get("local", "")) == host
                and str(entry.get("remote", "")).lower() == "localsubnet"):
                result["configured"] = True
                result["reason"] = "OK"
                return result
        result["reason"] = ("Vorhandene Regel weicht ab; keine automatische Aenderung"
                            if entries else "Dedizierte HTTPS-Regel fehlt")
    except (OSError, ValueError, UnicodeError, subprocess.TimeoutExpired):
        result["reason"] = "Firewall-Status nicht verfuegbar"
    return result
