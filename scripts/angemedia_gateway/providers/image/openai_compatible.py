"""OpenAI-compatible image adapter."""
from __future__ import annotations

from typing import Any

import httpx

from ... import config as C
from ...schemas import ImageRequest
from ..base import RouteTarget
from ..errors import BackendUnavailable, RateLimited


class OpenAICompatibleImageProvider:
    name = "openai_image"

    async def generate(self, req: ImageRequest, target: RouteTarget) -> dict[str, Any]:
        if not C.OPENAI_IMAGE_API_KEY:
            raise BackendUnavailable("OPENAI_IMAGE_API_KEY / OPENAI_API_KEY is not configured")

        payload: dict[str, Any] = {
            "model": target.model,
            "prompt": req.prompt,
            "n": 1,
            "size": req.size,
            "response_format": req.response_format,
        }
        if req.quality:
            payload["quality"] = req.quality
        if req.user:
            payload["user"] = req.user

        async with httpx.AsyncClient(timeout=C.HTTP_TIMEOUT) as client:
            resp = await client.post(
                f"{C.OPENAI_IMAGE_BASE_URL}/images/generations",
                headers={
                    "Authorization": f"Bearer {C.OPENAI_IMAGE_API_KEY}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )

        if resp.status_code == 401:
            raise BackendUnavailable("OpenAI-compatible image provider auth failed")
        if resp.status_code == 429:
            raise RateLimited("OpenAI-compatible image provider rate limited")
        if resp.status_code != 200:
            raise BackendUnavailable(f"OpenAI-compatible image provider 上游返回 HTTP {resp.status_code}", status_code=resp.status_code)

        data = resp.json()
        item = (data.get("data") or [{}])[0]
        if not item.get("url") and not item.get("b64_json"):
            raise BackendUnavailable("OpenAI-compatible image provider 未返回图片数据")
        return data

    def health(self) -> str:
        return "configured" if C.OPENAI_IMAGE_API_KEY else "not_configured"
