"""Tests für die Token-Prüfung schreibender AI-Node-Endpunkte."""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from app.security.api_token import (
    API_TOKEN_ENV_NAME,
    validate_api_token,
)

VALID_TOKEN = "a" * 48


def test_valid_api_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(API_TOKEN_ENV_NAME, VALID_TOKEN)

    validate_api_token(VALID_TOKEN)


def test_invalid_api_token_returns_401(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(API_TOKEN_ENV_NAME, VALID_TOKEN)

    with pytest.raises(HTTPException) as error:
        validate_api_token("falsch")

    assert error.value.status_code == 401


def test_missing_server_token_returns_503(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(API_TOKEN_ENV_NAME, raising=False)

    with pytest.raises(HTTPException) as error:
        validate_api_token(VALID_TOKEN)

    assert error.value.status_code == 503


def test_short_server_token_returns_503(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(API_TOKEN_ENV_NAME, "zu-kurz")

    with pytest.raises(HTTPException) as error:
        validate_api_token("zu-kurz")

    assert error.value.status_code == 503
