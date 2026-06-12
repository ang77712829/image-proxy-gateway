"""SiliconFlow image adapter."""
from __future__ import annotations

from typing import Any

import httpx

from ... import config as C
from ...media import openai_image_response
from ...schemas import ImageRequest
from ..base import RouteTarget
from ..errors import BackendUnavailable, RateLimited


class SiliconFlowProvider:
    name = "siliconflow"

    async def generate(self, req: ImageRequest, target: RouteTarget) -> dict[str, Any]:
        if not C.SILICONFLOW_API_KEY:
            raise BackendUnavailable("SILICONFLOW_API_KEY is not configured")

        image_size = req.size if req.size in C.KOLORS_SIZES else "1024x1024"
        payload = {
            "model": target.model,
            "prompt": req.prompt,
            "image_size": image_size,
            "batch_size": 1,
            "num_inference_steps": 20,
            "guidance_scale": 7.5,
        }

        async with httpx.AsyncClient(timeout=C.HTTP_TIMEOUT) as client:
            resp = await client.post(
                "https://api.siliconflow.cn/v1/images/generations",
                headers={
                    "Authorization": f"Bearer {C.SILICONFLOW_API_KEY}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )

        if resp.status_code == 401:
            raise BackendUnavailable("SiliconFlow API key is invalid or expired")
        if resp.status_code == 429:
            raise RateLimited("SiliconFlow rate limited")
        if resp.status_code != 200:
            raise BackendUnavailable(f"SiliconFlow 上游返回 HTTP {resp.status_code}", status_code=resp.status_code)

        data = resp.json()
        images = data.get("images") or []
        if not images or not images[0].get("url"):
            raise BackendUnavailable("SiliconFlow 未返回图片地址")
        return openai_image_response(url=images[0]["url"])

    def health(self) -> str:
        return "configured" if C.SILICONFLOW_API_KEY else "not_configured"
