from __future__ import annotations

import sys
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.main import app


@pytest.fixture(scope="module")
def client() -> Iterator[TestClient]:
    """Stellt einen gestarteten TestClient für die Smoke-Tests bereit."""

    with TestClient(app) as test_client:
        yield test_client


def print_result(
    name: str,
    success: bool,
    details: str = "",
) -> None:
    """Gibt das Ergebnis lesbar aus und lässt den Test sauber fehlschlagen."""

    marker = "OK" if success else "FEHLER"
    print(f"[{marker}] {name}")

    if details:
        print(f"       {details}")

    assert success, f"{name}: {details}"


def test_health(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200, (
        f"Health-Check: HTTP {response.status_code}: {response.text}"
    )

    data = response.json()
    status = data.get("status")

    print_result(
        "Health-Check",
        status == "healthy",
        f"Status: {status}",
    )


def test_openapi_routes(client: TestClient) -> None:
    response = client.get("/openapi.json")

    assert response.status_code == 200, (
        f"OpenAPI-Schema: HTTP {response.status_code}"
    )

    paths = response.json().get("paths", {})
    required = {
        "/knowledge/import/item",
        "/knowledge/import/relation",
        "/knowledge/import/merge",
    }

    missing = sorted(required - set(paths))

    print_result(
        "Knowledge-Import-Endpunkte",
        not missing,
        (
            "Alle 3 Endpunkte vorhanden."
            if not missing
            else f"Fehlend: {missing}"
        ),
    )
