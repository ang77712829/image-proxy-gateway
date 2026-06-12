"""Provider base interfaces."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from ..schemas import ImageRequest
from .errors import (  # noqa: F401
    BackendUnavailable,
    ProviderAuthError,
    ProviderError,
    ProviderProtocolError,
    ProviderRateLimited,
    ProviderTaskFailed,
    ProviderTimeout,
    ProviderUnavailable,
    ProviderValidationError,
    RateLimited,
)


@dataclass(frozen=True)
class RouteTarget:
    provider: str
    model: str


class ProviderBase(Protocol):
    name: str

    async def generate(self, req: ImageRequest, target: RouteTarget) -> dict:
        ...

    def health(self):
        ...
