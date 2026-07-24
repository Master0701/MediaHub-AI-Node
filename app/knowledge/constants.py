"""Rückwärtskompatible Exporte für bestehende Knowledge-Module."""
from app.knowledge.types import (
    DIRECTED_RELATION_TYPES,
    INVERSE_RELATION_TYPES,
    ORDER_TYPES,
    RELATION_ALIASES,
    SUPPORTED_RELATION_TYPES,
    SYMMETRIC_RELATION_TYPES,
    normalize_relation_type,
)

__all__ = [
    "DIRECTED_RELATION_TYPES", "INVERSE_RELATION_TYPES", "ORDER_TYPES",
    "RELATION_ALIASES", "SUPPORTED_RELATION_TYPES",
    "SYMMETRIC_RELATION_TYPES", "normalize_relation_type",
]
