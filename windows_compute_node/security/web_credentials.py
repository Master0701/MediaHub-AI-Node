"""Persistent, hashed credentials for the optional LAN HTTPS chat."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
from pathlib import Path

_ITERATIONS = 600_000


class NodeWebCredentials:
    def __init__(self, path: Path):
        self.path = Path(path)

    def configured(self) -> bool:
        return self.path.is_file()

    def set_credentials(self, username: str, password: str) -> None:
        username = username.strip()
        if not username or ":" in username or len(username) > 128:
            raise ValueError("Benutzername fehlt, ist zu lang oder enthaelt einen Doppelpunkt")
        if len(password) < 1 or len(password) > 1024:
            raise ValueError("Passwort muss 1 bis 1024 Zeichen haben")
        salt = secrets.token_bytes(32)
        digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _ITERATIONS)
        data = {
            "schema_version": 1,
            "username": username,
            "algorithm": "pbkdf2_sha256",
            "iterations": _ITERATIONS,
            "salt": salt.hex(),
            "hash": digest.hex(),
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_name(self.path.name + ".tmp")
        try:
            with tmp.open("x", encoding="utf-8") as handle:
                json.dump(data, handle, ensure_ascii=False, indent=2)
                handle.write("\n")
            os.replace(tmp, self.path)
        finally:
            tmp.unlink(missing_ok=True)

    def verify(self, username: str, password: str) -> bool:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if data.get("algorithm") != "pbkdf2_sha256":
                return False
            iterations = data["iterations"]
            if not isinstance(iterations, int) or not 100_000 <= iterations <= 2_000_000:
                return False
            salt = bytes.fromhex(data["salt"])
            digest = bytes.fromhex(data["hash"])
            if len(salt) != 32 or len(digest) != 32 or len(password) > 1024:
                return False
            candidate = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
            return hmac.compare_digest(username, data["username"]) and hmac.compare_digest(
                candidate, digest
            )
        except (OSError, ValueError, TypeError, KeyError, UnicodeError):
            return False
