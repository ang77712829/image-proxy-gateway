"""Shared provider HTTP helpers."""
from __future__ import annotations

from typing import Any

import httpx

from .. import config as C
from .errors import ProviderProtocolError, ProviderTimeout, ProviderUnavailable


def provider_timeout(timeout: float | None = None) -> httpx.Timeout:
    """Build the default provider timeout object."""

    value = C.HTTP_TIMEOUT if timeout is None else timeout
    return httpx.Timeout(value)


def safe_json_response(response: httpx.Response, *, provider: str, operation: str) -> Any:
    """Parse JSON without leaking raw upstream body in the raised error."""

    try:
        return response.json()
    except Exception as exc:
        raise ProviderProtocolError(
            f"{provider} {operation} returned invalid JSON",
            status_code=getattr(response, "status_code", None),
        ) from exc


def normalize_httpx_error(exc: Exception, *, provider: str, operation: str) -> ProviderUnavailable:
    """Map transport exceptions into structured provider errors."""

    if isinstance(exc, httpx.TimeoutException):
        return ProviderTimeout(f"{provider} {operation} timed out")
    return ProviderUnavailable(f"{provider} {operation} request failed", retryable=True, error_category="network")
