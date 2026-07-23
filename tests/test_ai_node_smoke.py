from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.main import app

client: TestClient | None = None


@pytest.fixture(scope="module", autouse=True)
def setup_client():
    global client

    with TestClient(app) as test_client:
        client = test_client
        yield


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
        (
            "Alle 3 Endpunkte vorhanden."
            if not missing
            else f"Fehlend: {missing}"
        ),
    )
