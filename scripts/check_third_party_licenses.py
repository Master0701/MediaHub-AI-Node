from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIREMENTS = ROOT / "requirements.txt"
LICENSE_DIR = ROOT / "licenses"
MAPPING = LICENSE_DIR / "dependency_licenses.json"
OVERVIEW = ROOT / "THIRD_PARTY_LICENSES.md"


def normalize_requirement(line: str) -> str:
    value = line.split("#", 1)[0].strip()
    if not value:
        return ""
    value = value.split(";", 1)[0].strip()
    value = re.split(r"[<>=!~\[]", value, maxsplit=1)[0].strip()
    return value.casefold().replace("_", "-")


def main() -> int:
    errors: list[str] = []
    for required in (REQUIREMENTS, LICENSE_DIR, MAPPING, OVERVIEW):
        if not required.exists():
            errors.append(f"Pflichtdatei fehlt: {required.relative_to(ROOT)}")

    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1

    mapping_data = json.loads(MAPPING.read_text(encoding="utf-8"))
    normalized_mapping = {
        key.casefold().replace("_", "-"): value
        for key, value in mapping_data.items()
    }
    requirements = {
        name
        for line in REQUIREMENTS.read_text(encoding="utf-8").splitlines()
        if (name := normalize_requirement(line))
    }

    missing = sorted(requirements - set(normalized_mapping))
    if missing:
        errors.append(
            "Nicht dokumentierte requirements.txt-Abhängigkeiten: "
            + ", ".join(missing)
        )

    for package, entry in normalized_mapping.items():
        if not entry.get("license"):
            errors.append(f"{package}: Lizenzkennung fehlt")
        files = list(entry.get("license_files") or [])
        if not files:
            errors.append(f"{package}: Lizenzdatei-Zuordnung fehlt")
        for filename in files:
            if not (LICENSE_DIR / filename).is_file():
                errors.append(f"{package}: licenses/{filename} fehlt")

    if errors:
        print("Lizenzprüfung fehlgeschlagen:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print(
        f"OK: {len(requirements)} direkte Python-Abhängigkeiten "
        "sind vollständig dokumentiert."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
