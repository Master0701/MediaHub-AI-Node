"""Resolve local .mhaiplugin dependency packages before one approved install.

No network or installation occurs while constructing a plan.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from .installer import PluginInstallError


def version(value: str) -> tuple[int, ...]:
    if not re.fullmatch(r"[0-9]+(?:\.[0-9]+)*", value):
        raise PluginInstallError(f"Ungueltige Plugin-Version: {value}")
    return tuple(map(int, value.split(".")))


def compatible(actual: str, minimum: str) -> bool:
    a, b = version(actual), version(minimum)
    size = max(len(a), len(b))
    return a + (0,) * (size - len(a)) >= b + (0,) * (size - len(b))


def dependencies(manifest: dict[str, Any]):
    items = manifest.get("dependencies", [])
    if not isinstance(items, list):
        raise PluginInstallError("Ungueltige Plugin-Abhaengigkeiten.")
    for item in items:
        if not isinstance(item, dict):
            raise PluginInstallError("Ungueltige Plugin-Abhaengigkeit.")
        targets = item.get("targets", [])
        if not isinstance(targets, list) or not all(isinstance(t, str) for t in targets):
            raise PluginInstallError("Ungueltige Abhaengigkeits-Ziele.")
        if targets and "windows_compute" not in targets:
            continue
        name = item.get("id")
        if (
            not isinstance(name, str)
            or not re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_.-]*", name)
            or name in (".", "..")
        ):
            raise PluginInstallError("Ungueltige Plugin-Abhaengigkeits-ID.")
        minimum = str(item.get("minimum_version") or "0")
        version(minimum)
        yield name, minimum


def resolve(installer, primary: Path, available: Path) -> list[dict[str, Any]]:
    """Dependency-first ordered plan; uses only locally supplied packages."""
    catalog: dict[str, tuple[Path, dict[str, Any]]] = {}
    if available.is_dir():
        for package in sorted(available.glob("*.mhaiplugin")):
            manifest = installer.inspect_package(package)
            key = manifest["id"]
            if key not in catalog or compatible(
                str(manifest["version"]), str(catalog[key][1]["version"])
            ):
                catalog[key] = (package, manifest)
    main_manifest = installer.inspect_package(primary)
    catalog[main_manifest["id"]] = (primary, main_manifest)
    ordered: list[dict[str, Any]] = []
    done: set[str] = set()
    visiting: set[str] = set()

    def walk(key: str, minimum: str, is_main: bool = False):
        if key in visiting:
            raise PluginInstallError(f"Zyklische Plugin-Abhaengigkeit: {key}")
        if key in done:
            if key in catalog and not compatible(str(catalog[key][1]["version"]), minimum):
                raise PluginInstallError(f"Abhaengigkeit {key} zu alt: mindestens {minimum}")
            return
        installed_path = installer.plugin_root / key / "plugin.json"
        installed = None
        if installed_path.is_file():
            try:
                installed = json.loads(installed_path.read_text(encoding="utf-8-sig"))
            except (ValueError, OSError) as exc:
                raise PluginInstallError(f"Installiertes Manifest unlesbar: {key}") from exc
            if not isinstance(installed, dict) or installed.get("id") != key:
                raise PluginInstallError(f"Installiertes Manifest ungueltig: {key}")
        if not is_main and installed and compatible(str(installed.get("version", "0")), minimum):
            done.add(key)
            return
        if key not in catalog:
            raise PluginInstallError(
                f"Abhaengigkeit fehlt: {key} (mindestens {minimum}). "
                "Bitte das .mhaiplugin-Paket im freigegebenen Paketkatalog bereitstellen."
            )
        package, manifest = catalog[key]
        if not compatible(str(manifest["version"]), minimum):
            raise PluginInstallError(f"Paket fuer {key} zu alt: mindestens {minimum}")
        visiting.add(key)
        for dep, needed in dependencies(manifest):
            walk(dep, needed)
        visiting.remove(key)
        done.add(key)
        digest = hashlib.sha256(package.read_bytes()).hexdigest()
        ordered.append({
            "plugin_id": key,
            "name": str(manifest.get("name") or key),
            "version": str(manifest["version"]),
            "package_path": str(package),
            "sha256": digest,
            "replace": bool(installed),
            "python_packages": (manifest.get("runtime") or {}).get("dependencies", []),
            "model": manifest.get("model"),
            "license": manifest.get("license"),
            "required_tools": manifest.get("required_tools", []),
        })

    walk(main_manifest["id"], "0", is_main=True)
    return ordered
