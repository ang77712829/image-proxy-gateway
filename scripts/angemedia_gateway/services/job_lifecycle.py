"""Safe job lifecycle side-effect helpers."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable

from ..repositories.jobs import create_job, update_job_status

log = logging.getLogger("angemedia-gateway")

CreateJobFunc = Callable[..., dict[str, Any]]
UpdateJobStatusFunc = Callable[..., dict[str, Any] | None]


@dataclass
class JobLifecycle:
    create_job_func: CreateJobFunc = create_job
    update_job_status_func: UpdateJobStatusFunc = update_job_status
    logger: logging.Logger = field(default=log)

    def create_safely(self, *, warning: str, **kwargs: Any) -> str | None:
        try:
            return str(self.create_job_func(**kwargs)["id"])
        except Exception:
            self.logger.warning(warning)
            return None

    def update_safely(self, job_id: str | None, *, warning: str, **kwargs: Any) -> dict[str, Any] | None:
        if not job_id:
            return None
        try:
            return self.update_job_status_func(job_id, **kwargs)
        except Exception:
            self.logger.warning(warning, job_id)
            return None

    def mark_running(
        self,
        job_id: str | None,
        *,
        kind: str,
        provider: str,
        model: str | None,
        started_at: str,
    ) -> dict[str, Any] | None:
        return self.update_safely(
            job_id,
            warning=f"更新 {kind} job running 状态失败: job_id=%s",
            status="running",
            provider=provider,
            model=model,
            started_at=started_at,
        )

    def mark_succeeded(
        self,
        job_id: str | None,
        *,
        kind: str,
        output_json: str | None = None,
        completed_at: str,
        duration_ms: int | None = None,
    ) -> dict[str, Any] | None:
        return self.update_safely(
            job_id,
            warning=f"更新 {kind} job succeeded 状态失败: job_id=%s",
            status="succeeded",
            output_json=output_json,
            completed_at=completed_at,
            duration_ms=duration_ms,
        )

    def mark_failed(
        self,
        job_id: str | None,
        *,
        kind: str,
        error_code: str,
        error_message: str,
        completed_at: str,
        error_category: str | None = None,
        human_hint: str | None = None,
        retryable: int | None = None,
        gateway_stage: str | None = None,
    ) -> dict[str, Any] | None:
        return self.update_safely(
            job_id,
            warning=f"更新 {kind} job failed 状态失败: job_id=%s",
            status="failed",
            error_code=error_code,
            error_message=error_message,
            error_category=error_category,
            human_hint=human_hint,
            retryable=retryable,
            gateway_stage=gateway_stage,
            completed_at=completed_at,
        )
