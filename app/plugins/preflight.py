"""Vorabprüfung von AI-Plugins vor der Installation."""

from __future__ import annotations

import importlib.metadata
import re
import shutil
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from zipfile import ZipFile

from app.plugins.errors import PluginError
from app.plugins.package_validator import ValidatedPluginPackage

LICENSE_FILENAMES = {
    "LICENSE",
    "LICENSE.txt",
    "LICENSE.md",
    "COPYING",
    "COPYING.txt",
}

REQUIREMENT_PATTERN = re.compile(
    r"^[A-Za-z0-9][A-Za-z0-9._-]*(?:\s*(?:==|>=|<=|~=|>|<)\s*[^\s;]+)?$"
)


class PluginPreflightError(PluginError):
    """Ein Plugin erfüllt die Installationsvoraussetzungen nicht."""


@dataclass(frozen=True, slots=True)
class DependencyCheck:
    """Prüfergebnis einer einzelnen Abhängigkeit."""

    name: str
    required: bool
    available: bool
    installed_version: str | None = None
    details: str = ""


@dataclass(frozen=True, slots=True)
class PluginPreflightResult:
    """Gesamtergebnis der Installationsvorprüfung."""

    plugin_id: str
    license_present: bool
    python_requirements: tuple[DependencyCheck, ...]
    required_tools: tuple[DependencyCheck, ...]
    plugin_dependencies: tuple[DependencyCheck, ...]
    warnings: tuple[str, ...] = ()

    @property
    def ready(self) -> bool:
        checks = (
            self.python_requirements
            + self.required_tools
            + self.plugin_dependencies
        )
        return self.license_present and all(
            not check.required or check.available
            for check in checks
        )


class PluginPreflightChecker:
    """Prüft Voraussetzungen und kann fehlende Punkte auch nur melden."""

    def __init__(
        self,
        *,
        installed_plugin_ids: Iterable[str] = (),
    ) -> None:
        self.installed_plugin_ids = {
            plugin_id.strip().lower()
            for plugin_id in installed_plugin_ids
        }

    def inspect(
        self,
        package: ValidatedPluginPackage,
    ) -> PluginPreflightResult:
        """Ermittelt alle Voraussetzungen, ohne bei fehlenden Punkten abzubrechen."""

        with ZipFile(package.archive_path) as archive:
            license_present = self._has_license(
                archive,
                package.root_directory,
            )
            requirements = self._read_requirements(
                archive,
                package.root_directory,
            )

        python_checks = tuple(
            self._check_python_requirement(requirement)
            for requirement in requirements
        )

        tool_checks = tuple(
            self._check_tool(tool)
            for tool in package.manifest.required_tools
        )

        plugin_checks = tuple(
            DependencyCheck(
                name=dependency.plugin_id,
                required=True,
                available=(
                    dependency.plugin_id in self.installed_plugin_ids
                ),
                details=(
                    f"Mindestversion: {dependency.minimum_version}"
                    if dependency.minimum_version
                    else ""
                ),
            )
            for dependency in package.manifest.dependencies
        )

        warnings: list[str] = []
        if not license_present:
            warnings.append("Im Plugin-Paket fehlt eine Lizenzdatei.")
        if not requirements:
            warnings.append(
                "Keine requirements.txt vorhanden; "
                "es werden keine Python-Abhängigkeiten geprüft."
            )

        return PluginPreflightResult(
            plugin_id=package.manifest.plugin_id,
            license_present=license_present,
            python_requirements=python_checks,
            required_tools=tool_checks,
            plugin_dependencies=plugin_checks,
            warnings=tuple(warnings),
        )

    def check(
        self,
        package: ValidatedPluginPackage,
    ) -> PluginPreflightResult:
        """Prüft streng und lehnt nicht erfüllte Voraussetzungen ab."""

        result = self.inspect(package)

        if not result.license_present:
            raise PluginPreflightError(
                "Im Plugin-Paket fehlt eine Lizenzdatei."
            )

        if not result.ready:
            missing = [
                check.name
                for check in (
                    result.python_requirements
                    + result.required_tools
                    + result.plugin_dependencies
                )
                if check.required and not check.available
            ]
            raise PluginPreflightError(
                "Fehlende Plugin-Voraussetzungen: "
                + ", ".join(missing)
            )

        return result

    @staticmethod
    def _check_tool(tool: str) -> DependencyCheck:
        available = shutil.which(tool) is not None
        return DependencyCheck(
            name=tool,
            required=True,
            available=available,
            details=(
                "Tool gefunden."
                if available
                else "Tool nicht im PATH gefunden."
            ),
        )

    @staticmethod
    def _has_license(
        archive: ZipFile,
        root_directory: str,
    ) -> bool:
        prefix = f"{root_directory}/"

        for name in archive.namelist():
            if not name.startswith(prefix):
                continue

            relative = name[len(prefix):]
            if "/" in relative.rstrip("/"):
                continue

            if Path(relative).name in LICENSE_FILENAMES:
                return True

        return False

    @staticmethod
    def _read_requirements(
        archive: ZipFile,
        root_directory: str,
    ) -> tuple[str, ...]:
        name = f"{root_directory}/requirements.txt"

        try:
            raw = archive.read(name).decode("utf-8")
        except KeyError:
            return ()

        requirements: list[str] = []

        for raw_line in raw.splitlines():
            line = raw_line.strip()

            if not line or line.startswith("#"):
                continue

            if not REQUIREMENT_PATTERN.fullmatch(line):
                raise PluginPreflightError(
                    f"Nicht unterstützte Python-Abhängigkeit: {line}"
                )

            requirements.append(line)

        return tuple(requirements)

    @staticmethod
    def _check_python_requirement(
        requirement: str,
    ) -> DependencyCheck:
        package_name = re.split(
            r"\s*(?:==|>=|<=|~=|>|<)\s*",
            requirement,
            maxsplit=1,
        )[0]

        try:
            version = importlib.metadata.version(package_name)
        except importlib.metadata.PackageNotFoundError:
            return DependencyCheck(
                name=requirement,
                required=True,
                available=False,
                details="Python-Paket nicht installiert.",
            )

        return DependencyCheck(
            name=requirement,
            required=True,
            available=True,
            installed_version=version,
            details="Python-Paket installiert.",
        )
