"""API-Token-Prüfung für zukünftige schreibende Endpunkte."""

from __future__ import annotations

import os
import secrets
from typing import Annotated

from fastapi import Header, HTTPException, status

API_TOKEN_ENV_NAME = "MEDIAHUB_AI_NODE_API_TOKEN"
MINIMUM_TOKEN_LENGTH = 32


class ApiTokenConfigurationError(RuntimeError):
    """Der Server besitzt keine sichere Token-Konfiguration."""


def get_configured_api_token() -> str:
    """Liest und validiert das konfigurierte Server-Token."""

    token = os.getenv(API_TOKEN_ENV_NAME, "").strip()

    if not token:
        raise ApiTokenConfigurationError(
            f"Die Umgebungsvariable {API_TOKEN_ENV_NAME} ist nicht gesetzt."
        )

    if len(token) < MINIMUM_TOKEN_LENGTH:
        raise ApiTokenConfigurationError(
            f"{API_TOKEN_ENV_NAME} muss mindestens "
            f"{MINIMUM_TOKEN_LENGTH} Zeichen lang sein."
        )

    return token


def validate_api_token(provided_token: str | None) -> None:
    """Prüft ein übergebenes Token mit konstantem Zeitverhalten."""

    try:
        configured_token = get_configured_api_token()
    except ApiTokenConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Schreibzugriffe sind auf diesem AI-Node nicht konfiguriert.",
        ) from exc

    candidate = (provided_token or "").strip()

    if not candidate or not secrets.compare_digest(
        candidate,
        configured_token,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Ungültiges oder fehlendes AI-Node-API-Token.",
            headers={"WWW-Authenticate": "Bearer"},
        )


def require_api_token(
    authorization: Annotated[str | None, Header()] = None,
) -> None:
    """FastAPI-Abhängigkeit für zukünftige geschützte Endpunkte."""

    prefix = "Bearer "
    provided_token = None

    if authorization and authorization.startswith(prefix):
        provided_token = authorization[len(prefix):]

    validate_api_token(provided_token)
