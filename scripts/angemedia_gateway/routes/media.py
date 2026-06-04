"""媒体生成、模型列表和小助手路由。"""
from __future__ import annotations

import logging
import os
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from .. import config as C
from ..assistant import assistant_enabled, build_assistant_plan
from ..providers.base import BackendUnavailable, RateLimited
from ..routing import MODEL_ALIASES, build_route_response, enhance_prompt_text
from ..schemas import AssistantRequest, EnhanceRequest, ImageRequest, RouteRequest, VideoRequest
from ..security import redact_secret_text
from ..services.media_service import (
    CustomProviderNotFound,
    ImageProvidersFailed,
    MediaService,
    NoImageProviderAvailable,
    VideoProviderDisabled,
)
from ..state import (
    builtin_provider_enabled,
    get_config,
    list_custom_providers,
)
from ..runtime import require_auth

log = logging.getLogger("angemedia-gateway")
router = APIRouter()
media_service = MediaService()


async def _create_image_response(req: ImageRequest) -> dict[str, Any]:
    try:
        return await media_service.create_image(req)
    except CustomProviderNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except NoImageProviderAvailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except RateLimited as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    except ImageProvidersFailed as exc:
        raise HTTPException(status_code=502, detail={"message": "all image providers failed", "errors": exc.errors}) from exc
    except BackendUnavailable as exc:
        raise HTTPException(status_code=502, detail=redact_secret_text(str(exc))) from exc


async def _create_video_response(req: VideoRequest) -> dict[str, Any]:
    try:
        return await media_service.create_video(req)
    except VideoProviderDisabled as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        log.exception("Agnes AI 视频生成失败")
        raise HTTPException(status_code=502, detail=f"Agnes AI 视频生成失败：{exc}") from exc


async def _get_video_response(task_id: str) -> dict[str, Any]:
    try:
        return await media_service.get_video(task_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        log.exception("Agnes AI 视频任务查询失败")
        raise HTTPException(status_code=502, detail=f"Agnes AI 视频任务查询失败：{redact_secret_text(str(exc))}") from exc


@router.get("/health")
async def health() -> dict[str, Any]:
    enabled_models = [name for name, target in MODEL_ALIASES.items() if builtin_provider_enabled(target.provider)]
    return {
        "name": "AngeMedia Gateway",
        "version": "v0.1.0",
        "status": "ok",
        "auth_enabled": bool(C.GATEWAY_API_KEY),
        "siliconflow": {
            "enabled": builtin_provider_enabled("siliconflow"),
            "configured": bool(C.SILICONFLOW_API_KEY),
        },
        "modelscope": {
            "enabled": builtin_provider_enabled("modelscope"),
            "configured": bool(C.MODELSCOPE_API_KEY),
        },
        "pollinations": {
            "enabled": builtin_provider_enabled("pollinations"),
            "configured": True,
        },
        "openai_image": {
            "enabled": builtin_provider_enabled("openai_image"),
            "configured": bool(C.OPENAI_IMAGE_API_KEY),
        },
        "agnes_image": {
            "enabled": builtin_provider_enabled("agnes_image"),
            "configured": bool(C.AGNES_API_KEY),
        },
        "agnes_video": {
            "enabled": builtin_provider_enabled("agnes_video"),
            "configured": bool(C.AGNES_API_KEY),
        },
        "storage_ready": C.OUTPUT_DIR.exists() and C.UPLOAD_DIR.exists() and C.DB_FILE.parent.exists(),
        "assistant": {
            "enabled": assistant_enabled(),
            "configured": bool(get_config("ANGE_LLM_API_KEY", os.getenv("ANGE_LLM_API_KEY", "")).strip()),
        },
        "models": enabled_models,
    }


@router.get("/v1/models", dependencies=[Depends(require_auth)])
async def list_models() -> dict[str, Any]:
    data = [
        {"id": name, "object": "model", "owned_by": target.provider, "enabled": True}
        for name, target in MODEL_ALIASES.items()
        if builtin_provider_enabled(target.provider)
    ]
    for provider in list_custom_providers(include_secret=False):
        if provider.get("enabled"):
            data.append({
                "id": f"custom:{provider['id']}",
                "object": "model",
                "owned_by": "custom_provider",
                "display_name": provider.get("name"),
                "default_model": provider.get("default_model"),
            })
    return {"object": "list", "data": data}


@router.post("/v1/media/route", dependencies=[Depends(require_auth)])
async def route_media(req: RouteRequest) -> dict[str, Any]:
    return build_route_response(req)


@router.post("/v1/prompt/enhance", dependencies=[Depends(require_auth)])
async def enhance_prompt(req: EnhanceRequest) -> dict[str, Any]:
    media_type = req.media_type if req.media_type != "auto" else build_route_response(RouteRequest(prompt=req.prompt))["media_type"]
    enhanced, changed, notes = enhance_prompt_text(req)
    return {
        "media_type": media_type,
        "original_prompt": req.prompt,
        "enhanced_prompt": enhanced,
        "changed": changed,
        "notes": notes,
    }


@router.post("/v1/assistant/plan", dependencies=[Depends(require_auth)])
async def assistant_plan(req: AssistantRequest) -> dict[str, Any]:
    try:
        return await build_assistant_plan(req)
    except BackendUnavailable as exc:
        raise HTTPException(status_code=502, detail=redact_secret_text(str(exc))) from exc


@router.post("/v1/assistant/generate", dependencies=[Depends(require_auth)])
async def assistant_generate(req: AssistantRequest) -> dict[str, Any]:
    try:
        plan = await build_assistant_plan(req)
    except BackendUnavailable as exc:
        raise HTTPException(status_code=502, detail=redact_secret_text(str(exc))) from exc
    if req.confirm_plan or get_config("ANGE_ASSISTANT_CONFIRM_PLAN", "false").lower() in {"1", "true", "yes", "on"}:
        return {"requires_confirmation": True, "plan": plan}

    if plan["media_type"] == "video":
        video_req = VideoRequest(
            prompt=plan["prompt"],
            model="agnes-video-v2.0",
            image=plan.get("image"),
            images=plan.get("images"),
            mode=plan.get("mode"),
            width=int(plan.get("width", 1152)),
            height=int(plan.get("height", 768)),
            num_frames=int(plan.get("num_frames", 121)),
            frame_rate=float(plan.get("frame_rate", 24)),
            wait_for_completion=bool(plan.get("wait_for_completion", req.wait_for_completion)),
        )
        result = await _create_video_response(video_req)
        result["assistant_plan"] = plan
        return result

    image_req = ImageRequest(
        prompt=plan["prompt"],
        model=plan.get("model"),
        size=plan.get("size", "1024x1024"),
        response_format="url",
        negative_prompt=plan.get("negative_prompt"),
    )
    result = await _create_image_response(image_req)
    result["assistant_plan"] = plan
    return result


@router.post("/v1/images/generations", dependencies=[Depends(require_auth)])
async def create_image(req: ImageRequest) -> dict[str, Any]:
    return await _create_image_response(req)


@router.post("/v1/videos", dependencies=[Depends(require_auth)])
async def create_video(req: VideoRequest) -> dict[str, Any]:
    return await _create_video_response(req)


@router.get("/v1/videos/{task_id}", dependencies=[Depends(require_auth)])
async def get_video(task_id: str) -> dict[str, Any]:
    return await _get_video_response(task_id)
