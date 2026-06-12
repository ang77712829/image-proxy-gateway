"""ModelScope image adapter."""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

import httpx

from ... import config as C
from ...media import openai_image_response
from ...schemas import ImageRequest
from ..base import RouteTarget
from ..errors import BackendUnavailable, RateLimited
from .quota import quota

log = logging.getLogger("angemedia-gateway")


class ModelScopeProvider:
    name = "modelscope"

    async def generate(self, req: ImageRequest, target: RouteTarget) -> dict[str, Any]:
        if not C.MODELSCOPE_API_KEY:
            raise BackendUnavailable("MODELSCOPE_API_KEY is not configured")
        if not await quota.available():
            raise RateLimited("local ModelScope quota is exhausted")

        base_url = "https://api-inference.modelscope.cn"
        async with httpx.AsyncClient(timeout=C.HTTP_TIMEOUT) as client:
            submit = await client.post(
                f"{base_url}/v1/images/generations",
                headers={
                    "Authorization": f"Bearer {C.MODELSCOPE_API_KEY}",
                    "Content-Type": "application/json",
                    "X-ModelScope-Async-Mode": "true",
                    "X-ModelScope-Task-Type": C.MODELSCOPE_SUBMIT_TASK_TYPE,
                },
                json={"model": target.model, "prompt": req.prompt, "n": 1},
            )

            if submit.status_code == 429:
                await quota.mark_exhausted()
                raise RateLimited("ModelScope remote quota is exhausted")
            if submit.status_code != 200:
                raise BackendUnavailable(f"ModelScope 提交任务失败：HTTP {submit.status_code}", status_code=submit.status_code)

            try:
                data = submit.json()
            except Exception as exc:
                raise BackendUnavailable("ModelScope 返回了非 JSON 响应") from exc

            task_id = data.get("task_id")
            if not task_id:
                raise BackendUnavailable("ModelScope 提交响应缺少 task_id")

            await quota.consume_one()
            log.info("ModelScope task submitted: model=%s task_id=%s remaining=%s", target.model, task_id, quota.remaining)

            deadline = time.time() + C.MAX_POLL_TIME
            while time.time() < deadline:
                await asyncio.sleep(C.POLL_INTERVAL)
                poll = await client.get(
                    f"{base_url}/v1/tasks/{task_id}",
                    headers={
                        "Authorization": f"Bearer {C.MODELSCOPE_API_KEY}",
                        "X-ModelScope-Task-Type": C.MODELSCOPE_POLL_TASK_TYPE,
                    },
                    timeout=20,
                )
                if poll.status_code == 429:
                    await quota.mark_exhausted()
                    raise RateLimited("ModelScope task polling rate limited")
                if poll.status_code != 200:
                    raise BackendUnavailable(f"ModelScope 轮询失败：HTTP {poll.status_code}", status_code=poll.status_code)

                task = poll.json()
                status = task.get("task_status", "")
                if status == "SUCCEED":
                    images = task.get("output_images") or []
                    if images:
                        return openai_image_response(url=images[0])
                    raise BackendUnavailable("ModelScope 任务成功但未返回图片")
                if status == "FAILED":
                    raise BackendUnavailable("ModelScope 任务失败")

        raise BackendUnavailable(f"ModelScope polling timed out after {C.MAX_POLL_TIME}s")

    def health(self) -> dict[str, Any]:
        return {
            "configured": bool(C.MODELSCOPE_API_KEY),
            "remaining_local_counter": quota.remaining,
            "daily_limit_local_counter": C.MODELSCOPE_DAILY_LIMIT,
        }
