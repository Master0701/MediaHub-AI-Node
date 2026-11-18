"""Lifecycle-managed, loopback-only Interaktions-KI browser bridge."""

from __future__ import annotations

import importlib.util
import ipaddress
import json
import os
import ssl
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path

from windows_compute_node.security.web_credentials import NodeWebCredentials
from windows_compute_node.service.tls_certificate import ensure_lan_certificate


class InteraktionsKIWebService:
    def __init__(self, api):
        self.api = api
        self.server = None
        self.thread = None
        self.bridge = None
        self.error = None
        self.http_error = None
        self.lan_error = None
        self.lan_server = None
        self.lan_thread = None

    def start(self):
        """Start both endpoints independently; preserve diagnostics without a console."""
        if self.bridge is not None:
            return
        self.error = None
        self.http_error = None
        self.lan_error = None
        plugin_id = "mediahub.interaktions_ki"
        if plugin_id not in self.api.plugin_loader.instances:
            self.error = "Interaktions-KI-Plugin ist nicht als aktive Instanz geladen"
            return
        plugin_dir = self.api.plugin_loader.plugin_root / plugin_id
        for folder in self.api.plugin_loader.discover():
            try:
                data = json.loads((folder / "plugin.json").read_text(encoding="utf-8-sig"))
            except (OSError, ValueError):
                continue
            if data.get("id") == plugin_id:
                plugin_dir = folder
                break
        script = plugin_dir / "web_bridge.py"
        page = plugin_dir / "web" / "index.html"
        if not script.is_file() or not page.is_file():
            self.error = "Web-Bridge oder Chatseite fehlt im installierten Plugin"
            return
        try:
            spec = importlib.util.spec_from_file_location(
                "mediahub_interaktions_ki_web_bridge", script
            )
            if spec is None or spec.loader is None:
                raise RuntimeError("Web-Bridge konnte nicht geladen werden")
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            db = Path.home() / ".mediahub" / "interaktions_ki_chats.sqlite3"
            db.parent.mkdir(parents=True, exist_ok=True)
            self.bridge = module.Bridge(page, db, "http://127.0.0.1:8766", self.api.api_token)
        except Exception as exc:
            self.error = f"Web-Bridge: {type(exc).__name__}: {exc}"
            print("Interaktions-KI Weboberflaeche nicht gestartet:", self.error, flush=True)
            return

        server = None
        try:
            server = ThreadingHTTPServer(("127.0.0.1", 8768), self.bridge.handler())
            server.daemon_threads = True
            thread = threading.Thread(
                target=server.serve_forever, name="interaktions-ki-web", daemon=True
            )
            self.server, self.thread = server, thread
            thread.start()
            print("Interaktions-KI Chat: http://127.0.0.1:8768/", flush=True)
        except Exception as exc:
            self.http_error = f"{type(exc).__name__}: {exc}"
            self.error = "HTTP: " + self.http_error
            print("Interaktions-KI HTTP nicht gestartet:", self.http_error, flush=True)
            self.server = self.thread = None
            if server is not None:
                server.server_close()

        # HTTPS must still be attempted when port 8768 is occupied.
        self.start_lan()

    def start_lan(self):
        if self.lan_server is not None:
            return
        host = os.environ.get("MEDIAHUB_INTERAKTIONS_KI_LAN_HOST", "").strip()
        self.lan_error = None
        if not host:
            return  # LAN disabled by default
        if self.bridge is None:
            self.lan_error = "Web-Bridge nicht initialisiert"
            return
        server = None
        try:
            ip = ipaddress.ip_address(host)
            # Loopback is permitted only for the isolated Stage-4 test runtime.
            test_runtime = Path(__file__).resolve().parents[2]
            test_marker = test_runtime / "STUFE4_HTTPS_LOOPBACK_TEST.marker"
            allow_test_loopback = (
                host == "127.0.0.1"
                and test_marker.is_file()
                and test_runtime.name == "MediaHub_HTTPS_Stufe4_Windows_Test"
            )
            if (
                ip.version != 4
                or ip.is_multicast
                or ip.is_unspecified
                or ip.is_global
                or (ip.is_loopback and not allow_test_loopback)
            ):
                raise ValueError("LAN_HOST muss eine lokale IPv4-Adresse sein")
            credentials = NodeWebCredentials(
                self.api.runtime_dir / "security" / "web_credentials.json"
            )
            if not credentials.configured():
                raise ValueError("HTTPS-Webzugang muss zuerst lokal eingerichtet werden")
            cert = os.environ.get("MEDIAHUB_INTERAKTIONS_KI_TLS_CERT", "")
            key = os.environ.get("MEDIAHUB_INTERAKTIONS_KI_TLS_KEY", "")
            if not cert and not key:
                cert_path, key_path = ensure_lan_certificate(
                    self.api.runtime_dir / "security", host
                )
                cert, key = str(cert_path), str(key_path)
            elif not cert or not key or not Path(cert).is_file() or not Path(key).is_file():
                raise ValueError("TLS-Zertifikat und Schluesseldatei muessen beide existieren")
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            context.minimum_version = ssl.TLSVersion.TLSv1_2
            context.load_cert_chain(certfile=cert, keyfile=key)
            server = ThreadingHTTPServer(
                (host, 8769), self.bridge.handler(lan_host=host, lan_credentials=credentials)
            )
            server.daemon_threads = True
            server.socket = context.wrap_socket(server.socket, server_side=True)
            thread = threading.Thread(
                target=server.serve_forever, name="interaktions-ki-lan-https", daemon=True
            )
            self.lan_server, self.lan_thread = server, thread
            thread.start()
            print(f"Interaktions-KI HTTPS im LAN: https://{host}:8769/", flush=True)
        except Exception as exc:
            self.lan_error = f"{type(exc).__name__}: {exc}"
            self.error = "LAN deaktiviert: " + self.lan_error
            print(self.error, flush=True)
            self.lan_server = self.lan_thread = None
            if server is not None:
                server.server_close()

    def status(self):
        return {
            "plugin_bridge": self.bridge is not None,
            "http": "bereit" if self.server is not None else "nicht gestartet",
            "https": "bereit"
            if self.lan_server is not None
            else (
                "deaktiviert"
                if not os.environ.get("MEDIAHUB_INTERAKTIONS_KI_LAN_HOST", "").strip()
                else "nicht gestartet"
            ),
            "http_error": self.http_error,
            "https_error": self.lan_error,
            "error": self.error,
        }

    def stop(self):
        lan_server, lan_thread = self.lan_server, self.lan_thread
        self.lan_server = self.lan_thread = None
        if lan_server is not None:
            lan_server.shutdown()
            lan_server.server_close()
        if lan_thread is not None and lan_thread.is_alive():
            lan_thread.join(timeout=5)
        server, thread, bridge = self.server, self.thread, self.bridge
        self.server = self.thread = self.bridge = None
        if server is not None:
            server.shutdown()
            server.server_close()
        if thread is not None and thread.is_alive():
            thread.join(timeout=5)
        if bridge is not None:
            with bridge.lock:
                bridge.db.close()
