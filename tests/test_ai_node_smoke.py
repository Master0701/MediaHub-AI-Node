from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi.testclient import TestClient

from app.database import SessionLocal
from app.knowledge.graph import KnowledgeGraphService
from app.main import app

client = TestClient(app)


def print_result(
    name: str,
    success: bool,
    details: str = "",
) -> bool:
    marker = "OK" if success else "FEHLER"

    print(f"[{marker}] {name}")

    if details:
        print(f"       {details}")

    return success


def test_health() -> bool:
    response = client.get("/health")

    if response.status_code != 200:
        return print_result(
            "Health-Check",
            False,
            f"HTTP {response.status_code}: {response.text}",
        )

    data = response.json()
    status = data.get("status")

    return print_result(
        "Health-Check",
        status == "healthy",
        f"Status: {status}",
    )


def test_openapi_routes() -> bool:
    response = client.get("/openapi.json")

    if response.status_code != 200:
        return print_result(
            "OpenAPI-Schema",
            False,
            f"HTTP {response.status_code}",
        )

    paths = response.json().get("paths", {})

    required = {
        "/knowledge/import/item",
        "/knowledge/import/relation",
        "/knowledge/import/merge",
    }

    missing = sorted(required - set(paths))

    return print_result(
        "Knowledge-Import-Endpunkte",
        not missing,
        ("Alle 3 Endpunkte vorhanden." if not missing else f"Fehlend: {missing}"),
    )


def test_item_import() -> bool:
    payload: dict[str, Any] = {
        "title": "Creed II",
        "media_type": "movie",
        "year": 2018,
        "external_ids": {
            "tmdb": "480530",
            "imdb": "tt6343314",
        },
        "metadata": {
            "franchise": "Rocky / Creed",
            "collection": "Creed",
        },
        "source": "smoke_test",
        "dry_run": True,
    }

    response = client.post(
        "/knowledge/import/item",
        json=payload,
    )

    if response.status_code != 200:
        return print_result(
            "Wissenseintrag-Import",
            False,
            f"HTTP {response.status_code}: {response.text}",
        )

    data = response.json()
    status = data.get("status")
    item_id = data.get("item_id")

    valid = (
        status
        in {
            "would_update",
            "unchanged",
        }
        and item_id == 3
    )

    return print_result(
        "Wissenseintrag-Import",
        valid,
        f"Status: {status}, Eintrag: {item_id}",
    )


def test_relation_import() -> bool:
    payload: dict[str, Any] = {
        "source": {
            "item_id": 3,
        },
        "target": {
            "item_id": 2,
        },
        "relation_type": "sequel-of",
        "order_type": "release-order",
        "position": 2,
        "notes": ("Creed II setzt die Handlung von Creed fort."),
        "dry_run": True,
    }

    response = client.post(
        "/knowledge/import/relation",
        json=payload,
    )

    if response.status_code != 200:
        return print_result(
            "Beziehungsimport",
            False,
            f"HTTP {response.status_code}: {response.text}",
        )

    data = response.json()
    status = data.get("status")
    relation_id = data.get("relation_id")

    valid = status == "unchanged" and relation_id == 2

    return print_result(
        "Beziehungsimport",
        valid,
        (f"Status: {status}, Beziehung: {relation_id}"),
    )


def test_graph_integrity() -> bool:
    db = SessionLocal()

    try:
        service = KnowledgeGraphService(db)
        result = service.find_invalid_relations()
    finally:
        db.close()

    invalid_count = result.get(
        "invalid_count",
        -1,
    )

    duplicate_count = result.get(
        "duplicate_count",
        -1,
    )

    valid = invalid_count == 0 and duplicate_count == 0

    return print_result(
        "Graph-Integrität",
        valid,
        (f"Ungültig: {invalid_count}, Dubletten: {duplicate_count}"),
    )


def main() -> int:
    print()
    print("MediaHub-KI-Knoten Abschlusstest")
    print("=" * 38)

    results = [
        test_health(),
        test_openapi_routes(),
        test_item_import(),
        test_relation_import(),
        test_graph_integrity(),
    ]

    print("=" * 38)

    passed = sum(results)
    total = len(results)

    print(f"Bestanden: {passed} von {total}")

    if all(results):
        print("Gesamtergebnis: ERFOLGREICH")
        return 0

    print("Gesamtergebnis: FEHLER")
    return 1


if __name__ == "__main__":
    sys.exit(main())
