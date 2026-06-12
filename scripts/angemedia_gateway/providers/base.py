"""Provider 基础类型与结构化异常。"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from ..schemas import ImageRequest


# ── 结构化 Provider 异常 ────────────────────────────────────────


@dataclass
class ProviderError(RuntimeError):
    """所有 Provider 异常的结构化基类。

    Attributes:
        message: 安全摘要，不含 raw body / secret / traceback。
        status_code: 上游 HTTP 状态码，连接失败时为 None。
        retryable: 是否可重试（供后续 retry / circuit breaker 使用）。
        error_category: 错误分类，用于 diagnostics 和 safe envelope。
    """

    message: str
    status_code: int | None = None
    retryable: bool = False
    error_category: str = "upstream"

    def __post_init__(self) -> None:
        RuntimeError.__init__(self, self.message)

    def __str__(self) -> str:
        return self.message


class ProviderAuthError(ProviderError):
    """401 / 403 鉴权失败。"""

    def __init__(self, message: str, *, status_code: int | None = 401) -> None:
        super().__init__(message=message, status_code=status_code, retryable=False, error_category="auth")


class ProviderRateLimited(ProviderError):
    """429 限流。"""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = 429,
        retryable: bool = True,
        error_category: str = "rate_limit",
    ) -> None:
        super().__init__(message=message, status_code=status_code, retryable=retryable, error_category=error_category)


class ProviderTimeout(ProviderError):
    """连接或读取超时。"""

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message=message, status_code=status_code, retryable=True, error_category="timeout")


class ProviderUnavailable(ProviderError):
    """上游服务不可用（5xx / 连接失败）。"""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        retryable: bool = False,
        error_category: str = "upstream",
    ) -> None:
        super().__init__(message=message, status_code=status_code, retryable=retryable, error_category=error_category)


class ProviderValidationError(ProviderError):
    """请求参数校验失败（400）。"""

    def __init__(self, message: str, *, status_code: int | None = 400) -> None:
        super().__init__(message=message, status_code=status_code, retryable=False, error_category="validation")


# ── 兼容旧异常 ──────────────────────────────────────────────────
#
# BackendUnavailable 和 RateLimited 是 v0.2.0 之前就存在的异常。
# 现有 image.py / custom.py / media_service.py 全部使用这两个类。
# 改为继承 ProviderError 子类，保留旧接口完全兼容：
#   - raise BackendUnavailable("msg") 仍然工作
#   - raise RateLimited("msg") 仍然工作
#   - except BackendUnavailable / except RateLimited 仍然捕获
#   - str(exc) 只返回 message
#


class BackendUnavailable(ProviderUnavailable):
    """后端不可用（兼容旧接口）。"""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        retryable: bool = False,
        error_category: str = "upstream",
    ) -> None:
        super().__init__(message=message, status_code=status_code, retryable=retryable, error_category=error_category)


class RateLimited(ProviderRateLimited):
    """后端限流或额度耗尽（兼容旧接口）。"""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = 429,
        retryable: bool = True,
        error_category: str = "rate_limit",
    ) -> None:
        super().__init__(message=message, status_code=status_code, retryable=retryable, error_category=error_category)


# ── Provider 接口 ───────────────────────────────────────────────


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
