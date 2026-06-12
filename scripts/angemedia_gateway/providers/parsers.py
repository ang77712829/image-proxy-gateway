"""Small shared parser helpers for provider adapters."""
from __future__ import annotations

from typing import Any

from fastapi import HTTPException

from .errors import ProviderProtocolError


def parse_size(size: str) -> tuple[int, int]:
    try:
        width_text, height_text = size.lower().split("x", 1)
        width, height = int(width_text), int(height_text)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid size format: {size!r}, expected WIDTHxHEIGHT") from exc
    if width <= 0 or height <= 0:
        raise HTTPException(status_code=400, detail=f"Invalid size: {size!r}")
    return width, height


def require_mapping(value: Any, *, provider: str, operation: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ProviderProtocolError(f"{provider} {operation} returned a non-object response")
    return value


def first_string_field(data: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = data.get(key)
        if isinstance(value, str) and value:
            return value
    return None
