"""自定义 Provider 运行时。"""
from __future__ import annotations

from typing import Any

from ..schemas import ImageRequest
from ..security import ensure_public_http_url
from .base import BackendUnavailable
from .http import provider_client, request_with_provider_errors, safe_json_response
from .parsers import require_mapping


async def generate_custom_openai_image(req: ImageRequest, provider: dict[str, Any]) -> dict[str, Any]:
    """调用 OpenAI-compatible 图片接口。

    自定义渠道的最小约定：
    - base_url 指向 OpenAI-compatible v1 根地址；
    - 生成接口为 {base_url}/images/generations；
    - 响应包含 data[0].url 或 data[0].b64_json。
    """
    if not provider.get("enabled"):
        raise BackendUnavailable("自定义渠道已停用")

    try:
        base_url = ensure_public_http_url(str(provider.get("base_url") or "").rstrip("/"))
    except ValueError as exc:
        raise BackendUnavailable(str(exc)) from exc
    api_key = str(provider.get("api_key") or "")
    model = str(req.provider_model or provider.get("default_model") or "")
    if not base_url or not model:
        raise BackendUnavailable("自定义渠道缺少 base_url 或 default_model")

    payload: dict[str, Any] = {
        "model": model,
        "prompt": req.prompt,
        "n": 1,
        "size": req.size,
        "response_format": req.response_format,
    }
    if req.quality:
        payload["quality"] = req.quality
    if req.user:
        payload["user"] = req.user
    if req.negative_prompt:
        payload["negative_prompt"] = req.negative_prompt
    if req.seed is not None:
        payload["seed"] = req.seed

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    async with provider_client() as client:
        resp = await request_with_provider_errors(
            client,
            "POST",
            f"{base_url}/images/generations",
            provider="custom image provider",
            operation="generate",
            headers=headers,
            json=payload,
        )

    data = require_mapping(
        safe_json_response(resp, provider="custom image provider", operation="generate"),
        provider="custom image provider",
        operation="generate",
    )
    item_list = data.get("data") or [{}]
    item = item_list[0] if isinstance(item_list, list) and item_list else {}
    if not isinstance(item, dict) or (not item.get("url") and not item.get("b64_json")):
        raise BackendUnavailable("自定义渠道没有返回图片数据")
    return data
