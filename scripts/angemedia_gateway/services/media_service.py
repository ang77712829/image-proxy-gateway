"""Media generation business orchestration."""
from __future__ import annotations

import logging
import time
from typing import Any

from ..media import localize_image_result, localize_video_result, maybe_to_b64
from ..providers.base import BackendUnavailable, RateLimited
from ..providers.custom import generate_custom_openai_image
from ..routing import resolve_chain
from ..schemas import ImageRequest, VideoRequest
from ..security import validate_task_id
from ..state import (
    builtin_provider_enabled,
    get_custom_provider,
    now_iso,
    record_generation,
    upsert_video_task,
)
from ..runtime import PROVIDERS, agnes_video

log = logging.getLogger("angemedia-gateway")


class CustomProviderNotFound(RuntimeError):
    """Requested custom provider does not exist."""


class NoImageProviderAvailable(RuntimeError):
    """No enabled image provider can handle the request."""


class ImageProvidersFailed(RuntimeError):
    """All image providers in the resolved chain failed."""

    def __init__(self, errors: list[str]) -> None:
        super().__init__("all image providers failed")
        self.errors = errors


class VideoProviderDisabled(RuntimeError):
    """Video provider is disabled in current runtime config."""


class MediaService:
    async def create_image(self, req: ImageRequest) -> dict[str, Any]:
        if req.model and req.model.startswith("custom:"):
            return await self._create_custom_image(req)
        return await self._create_builtin_image(req)

    async def _create_custom_image(self, req: ImageRequest) -> dict[str, Any]:
        provider_id = req.model.split(":", 1)[1] if req.model else ""
        provider = get_custom_provider(provider_id, include_secret=True)
        if provider is None:
            raise CustomProviderNotFound(f"自定义渠道不存在：{provider_id}")

        started_at = now_iso()
        started = time.perf_counter()
        result = await generate_custom_openai_image(req, provider)
        if req.response_format == "url":
            result = await localize_image_result(result, f"custom_{provider_id}", provider.get("default_model", "custom"))
        elif req.response_format == "b64_json":
            result = await maybe_to_b64(result, req.response_format)

        duration_ms = int((time.perf_counter() - started) * 1000)
        result["provider"] = f"custom:{provider_id}"
        result["model"] = str(provider.get("default_model") or f"custom:{provider_id}")
        result["duration_ms"] = duration_ms
        record_id = record_generation(
            media_type="image",
            prompt=req.prompt,
            enhanced_prompt=None,
            model=f"custom:{provider_id}",
            status="completed",
            result=result,
            provider=f"custom:{provider_id}",
            request_model=req.model,
            input_mode="custom_provider",
            duration_ms=duration_ms,
            started_at=started_at,
        )
        result["history_id"] = record_id
        return result

    async def _create_builtin_image(self, req: ImageRequest) -> dict[str, Any]:
        chain = resolve_chain(req.model)
        if not chain:
            raise NoImageProviderAvailable("当前没有可用图片渠道：所选模型已停用或默认链路全部停用")

        errors: list[str] = []
        for target in chain:
            backend = target.provider
            model = target.model
            provider = PROVIDERS.get(backend)
            if provider is None:
                errors.append(f"{backend}/{model}: unknown provider")
                continue

            try:
                started_at = now_iso()
                started = time.perf_counter()
                result = await provider.generate(req, target)
                if req.response_format == "url":
                    result = await localize_image_result(result, backend, model)
                elif backend != "pollinations":
                    result = await maybe_to_b64(result, req.response_format)

                duration_ms = int((time.perf_counter() - started) * 1000)
                result["provider"] = backend
                result["model"] = model
                result["request_model"] = req.model or ""
                result["duration_ms"] = duration_ms
                record_id = record_generation(
                    media_type="image",
                    prompt=req.prompt,
                    enhanced_prompt=None,
                    model=model,
                    status="completed",
                    result=result,
                    provider=backend,
                    request_model=req.model or "",
                    input_mode="default_chain" if not req.model else "explicit_model",
                    duration_ms=duration_ms,
                    started_at=started_at,
                )
                result["history_id"] = record_id
                log.info("%s succeeded: model=%s", backend, model)
                return result
            except RateLimited as exc:
                message = f"{backend}/{model}: {exc}"
                log.warning(message)
                errors.append(message)
                continue
            except BackendUnavailable as exc:
                message = f"{backend}/{model}: {exc}"
                log.warning(message)
                errors.append(message)
                continue
            except Exception as exc:
                message = f"{backend}/{model}: unexpected {type(exc).__name__}: {exc}"
                log.exception(message)
                errors.append(message)
                continue

        raise ImageProvidersFailed(errors)

    async def create_video(self, req: VideoRequest) -> dict[str, Any]:
        if not builtin_provider_enabled("agnes_video"):
            raise VideoProviderDisabled("Agnes 视频渠道已停用，请在管理后台恢复后再生成")

        started_at = now_iso()
        started = time.perf_counter()
        if req.wait_for_completion:
            result = await agnes_video.generate_video(req)
            result = await localize_video_result(result)
            status = str(result.get("status") or "completed")
        else:
            result = await agnes_video.submit_task(req)
            status = str(result.get("status") or "submitted")

        duration_ms = int((time.perf_counter() - started) * 1000)
        result["provider"] = "agnes_video"
        result["model"] = req.model
        result["duration_ms"] = duration_ms
        task_id = str(result.get("task_id") or result.get("id") or "")
        if task_id:
            upsert_video_task(task_id, req.prompt, req.model, status, result, duration_ms=duration_ms)
        record_id = record_generation(
            media_type="video",
            prompt=req.prompt,
            enhanced_prompt=None,
            model=req.model,
            status=status,
            result=result,
            task_id=task_id or None,
            provider="agnes_video",
            request_model=req.model,
            input_mode=req.mode or ("image" if req.image or req.images else "text"),
            duration_ms=duration_ms,
            started_at=started_at,
        )
        result["history_id"] = record_id
        return result

    async def get_video(self, task_id: str) -> dict[str, Any]:
        safe_task_id = validate_task_id(task_id)
        result = await agnes_video.poll_task(safe_task_id)
        result = await localize_video_result(result)
        upsert_video_task(
            safe_task_id,
            str(result.get("prompt") or ""),
            str(result.get("model") or "agnes-video-v2.0"),
            str(result.get("status") or "unknown"),
            result,
            duration_ms=int(result.get("duration_ms") or 0),
        )
        return result
