"""Determine the private IPv4 address of the Windows default route."""

import ipaddress
import socket


def valid_lan_ipv4(value):
    try:
        ip = ipaddress.IPv4Address(value)
    except ValueError:
        return False
    return ip.is_private and not (
        ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_unspecified
    )


def resolve_lan_host(config, override=""):
    override = override.strip()
    if override:
        if not valid_lan_ipv4(override):
            raise ValueError("Ungueltige LAN-IPv4 in Umgebungsvariable")
        return override
    mode = str(config.get("mode", "auto")).lower()
    if mode == "disabled":
        return ""
    if mode == "manual":
        host = str(config.get("host", "")).strip()
        if not valid_lan_ipv4(host):
            raise ValueError("Ungueltige manuelle LAN-IPv4")
        return host
    if mode != "auto":
        raise ValueError("LAN-Modus muss auto, manual oder disabled sein")
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("1.1.1.1", 443))
            host = sock.getsockname()[0]
        return host if valid_lan_ipv4(host) else ""
    except OSError:
        return ""
