"""Consent-gated Windows HTTPS firewall setup for the Compute Node.

Only the dedicated named rule is created; existing rules are never modified.
"""

from __future__ import annotations

import ctypes
import ipaddress
import sys

from windows_compute_node.service.https_firewall import RULE_NAME, firewall_status


def request_rule_setup(host: str, port: int = 8769) -> str:
    """Ask Windows UAC to create the dedicated rule; return launch status only."""
    if sys.platform != "win32":
        return "Windows erforderlich"
    try:
        ip = ipaddress.ip_address(host)
        if ip.version != 4 or not ip.is_private or ip.is_loopback:
            return "Keine gueltige private LAN-IPv4-Adresse"
        if not isinstance(port, int) or not 1 <= port <= 65535:
            return "Ungueltiger Port"
    except ValueError:
        return "Ungueltige LAN-Adresse"
    if firewall_status(host, port).get("configured"):
        return "Regel bereits vorhanden"
    # The host is validated as IPv4; the rule name is a fixed application constant.
    script = (
        "$ErrorActionPreference='Stop'; "
        f"$n='{RULE_NAME}'; "
        "$existing=@(Get-NetFirewallRule -DisplayName $n -ErrorAction SilentlyContinue); "
        "if($existing.Count -gt 0){"
        "Write-Host 'Regelname bereits vorhanden; keine Aenderung'; "
        "exit 2}; "
        f"New-NetFirewallRule -DisplayName $n -Direction Inbound -Action Allow "
        f"-Protocol TCP -LocalPort {port} -LocalAddress {host} "
        "-RemoteAddress LocalSubnet -Profile Private | Out-Null"
    )
    encoded = __import__("base64").b64encode(script.encode("utf-16-le")).decode("ascii")
    args = f"-NoProfile -NonInteractive -ExecutionPolicy Bypass -EncodedCommand {encoded}"
    try:
        result = ctypes.windll.shell32.ShellExecuteW(None, "runas", "powershell.exe", args, None, 1)
        if result <= 32:
            return "Administratorabfrage abgebrochen oder fehlgeschlagen"
        return "Administratorabfrage gestartet; Regelstatus erneut pruefen"
    except (AttributeError, OSError) as exc:
        return f"Administratorabfrage fehlgeschlagen: {type(exc).__name__}"
