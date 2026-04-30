运行
from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request

from ..core.engine import PromptEngine
from ..core.models import PromptTemplate, TestResult
from ..core.storage import Storage
from .schemas import (
    AIProviderSettingsRequest,
    AIProviderSettingsResponse,
    AnalyticsResponse,
    ChatRequest,
    ChatResponse,
    CreateTemplateRequest,
    EvaluatePromptRequest,
    GenerateVariantsRequest,
    OptimizePromptRequest,
    PromptTemplateResponse,
    RenderTemplateRequest,
    RenderTemplateResponse,
    TestResultResponse,
    UpdateTemplateRequest,
    template_to_response,
    test_result_to_response,
)


router = APIRouter()

PROVIDER_CONFIG_PATH = Path(
    os.getenv("PROMPTFORGE_PROVIDER_CONFIG", "promptforge_provider.json")
)

DEFAULT_PROVIDER_CONFIG: Dict[str, str] = {
    "provider": "openai",
    "model": "gpt-4o-mini",
    "api_base": "https://api.openai.com/v1",
    "api_key": "",
}

DEFAULT_API_BASES: Dict[str, str] = {
    "openai": "https://api.openai.com/v1",
    "anthropic": "https://api.anthropic.com/v1",
    "custom": "",
}


def get_storage(request: Request) -> Storage:
    storage = getattr(request.app.state, "storage", None)
    if storage is None:
        raise HTTPException(status_code=500, detail="存储服务未初始化")
    return storage


def model_dump_compat(model: Any, **kwargs: Any) -> Dict[str, Any]:
    if hasattr(model, "model_dump"):
        return model.model_dump(**kwargs)
    return model.dict(**kwargs)


def read_provider_config() -> Dict[str, Any]:
    if not PROVIDER_CONFIG_PATH.exists():
        return DEFAULT_PROVIDER_CONFIG.copy()

    try:
        with PROVIDER_CONFIG_PATH.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except (OSError, json.JSONDecodeError):
        return DEFAULT_PROVIDER_CONFIG.copy()

    config = DEFAULT_PROVIDER_CONFIG.copy()
    config.update({key: value for key, value in data.items() if value is not None})

    provider = config.get("provider") or "openai"
    if not config.get("api_base"):
        config["api_base"] = DEFAULT_API_BASES.get(provider, "")

    return config


def write_provider_config(config: Dict[str, Any]) -> None:
    if PROVIDER_CONFIG_PATH.parent != Path("."):
        PROVIDER_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)

    with PROVIDER_CONFIG_PATH.open("w", encoding="utf-8") as file:
        json.dump(config, file, ensure_ascii=False, indent=2)


def mask_api_key(api_key: Optional[str]) -> str:
    if not api_key:
        return ""

    if len(api_key) <= 8:
        return "****"

    return f"{api_key[:4]}...{api_key[-4:]}"


def public_provider_config(config: Dict[str, Any]) -> AIProviderSettingsResponse:
    provider = config.get("provider") or "openai"
    api_base = config.get("api_base") or DEFAULT_API_BASES.get(provider, "")

    return AIProviderSettingsResponse(
        provider=provider,
        model=config.get("model") or DEFAULT_PROVIDER_CONFIG["model"],
        api_base=api_base,
        api_key=mask_api_key(config.get("api_key")),
        configured=bool(config.get("api_key")),
    )


def normalize_chat_url(api_base: str, provider: str) -> str:
    base = (api_base or DEFAULT_API_BASES.get(provider, "")).rstrip("/")

    if not base:
        raise HTTPException(status_code=400, detail="请先配置 API 地址")

    if base.endswith("/chat/completions") or base.endswith("/messages"):
        return base

    if provider in {"openai", "custom"}:
        return f"{base}/chat/completions"

    if provider == "anthropic":
        return f"{base}/messages"

    raise HTTPException(status_code=400, detail="不支持的 AI 服务商")


def extract_provider_error(payload: Any) -> str:
    if isinstance(payload, dict):
        error = payload.get("error")

        if isinstance(error, dict):
            return str(error.get("message") or error.get("type") or "AI 服务调用失败")

        if isinstance(error, str):
            return error

        if payload.get("message"):
            return str(payload["message"])

        if payload.get("detail"):
            return str(payload["detail"])

    if isinstance(payload, str) and payload.strip():
        return payload[:300]

    return "AI 服务调用失败"


async def call_openai_compatible_provider(
    *,
    provider: str,
    api_key: str,
    api_base: str,
    model: str,
    prompt: str,
) -> Dict[str, Any]:
    url = normalize_chat_url(api_base, provider)

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    body = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": prompt,
            }
        ],
        "temperature": 0.7,
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(url, headers=headers, json=body)

    content_type = response.headers.get("content-type", "")
    payload: Any

    if "application/json" in content_type:
        payload = response.json()
    else:
        payload = response.text

    if response.status_code >= 400:
        raise HTTPException(
            status_code=502,
            detail=f"AI 服务调用失败：{extract_provider_error(payload)}",
        )

    if not isinstance(payload, dict):
        raise HTTPException(status_code=502, detail="AI 服务返回格式不正确")

    choices = payload.get("choices") or []
    first_choice = choices[0] if choices else {}
    message = first_choice.get("message") or {}
    content = message.get("content") or first_choice.get("text") or ""

    usage = payload.get("usage") or {}
    token_usage = (
        usage.get("total_tokens")
        or usage.get("completion_tokens")
        or usage.get("prompt_tokens")
        or 0
    )

    return {
        "response": content,
        "raw_response": payload,
        "token_usage": int(token_usage or 0),
    }


async def call_anthropic_provider(
    *,
    api_key: str,
    api_base: str,
    model: str,
    prompt: str,
) -> Dict[str, Any]:
    url = normalize_chat_url(api_base, "anthropic")

    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    body = {
        "model": model,
        "max_tokens": 1024,
        "messages": [
            {
                "role": "user",
                "content": prompt,
            }
        ],
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(url, headers=headers, json=body)

    content_type = response.headers.get("content-type", "")
    payload: Any

    if "application/json" in content_type:
        payload = response.json()
    else:
        payload = response.text

    if response.status_code >= 400:
        raise HTTPException(
            status_code=502,
            detail=f"AI 服务调用失败：{extract_provider_error(payload)}",
        )

    if not isinstance(payload, dict):
        raise HTTPException(status_code=502, detail="AI 服务返回格式不正确")

    content_blocks = payload.get("content") or []
    response_text_parts: List[str] = []

    for block in content_blocks:
        if isinstance(block, dict) and block.get("type") == "text":
            response_text_parts.append(str(block.get("text") or ""))
        elif isinstance(block, str):
            response_text_parts.append(block)

    response_text = "\n".join(part for part in response_text_parts if part).strip()

    usage = payload.get("usage") or {}
    token_usage = int(usage.get("input_tokens") or 0) + int(
        usage.get("output_tokens") or 0
    )

    return {
        "response": response_text,
        "raw_response": payload,
        "token_usage": token_usage,
    }


async def call_ai_provider(config: Dict[str, Any], prompt: str) -> Dict[str, Any]:
    provider = config.get("provider") or "openai"
    api_key = config.get("api_key") or ""
    model = config.get("model") or ""
    api_base = config.get("api_base") or DEFAULT_API_BASES.get(provider, "")

    if provider not in {"openai", "anthropic", "custom"}:
        raise HTTPException(status_code=400, detail="不支持的 AI 服务商")

    if not api_key:
        raise HTTPException(status_code=400, detail="请先保存 API 密钥")

    if not model:
        raise HTTPException(status_code=400, detail="请先选择模型")

    if provider == "anthropic":
        return await call_anthropic_provider(
            api_key=api_key,
            api_base=api_base,
            model=model,
            prompt=prompt,
        )

    return await call_openai_compatible_provider(
        provider=provider,
        api_key=api_key,
        api_base=api_base,
        model=model,
        prompt=prompt,
    )


@router.post("/templates/", response_model=PromptTemplateResponse)
async def create_template(
    request_body: CreateTemplateRequest,
    storage: Storage = Depends(get_storage),
) -> PromptTemplateResponse:
    now = datetime.now(timezone.utc)
    template = PromptTemplate(
        id=0,
        name=request_body.name,
        content=request_body.content,
        category=request_body.category,
        tags=request_body.tags,
        variables=request_body.variables,
        version=request_body.version,
        created_at=now,
        updated_at=now,
        metadata=request_body.metadata,
    )
    template.id = storage.save_template(template)
    return template_to_response(template)


@router.put("/templates/{template_id}", response_model=PromptTemplateResponse)
async def update_template(
    template_id: int,
    request_body: UpdateTemplateRequest,
    storage: Storage = Depends(get_storage),
) -> PromptTemplateResponse:
    existing = storage.get_template(template_id)
    if not existing:
        raise HTTPException(status_code=404, detail="模板不存在")

    template = PromptTemplate(
        id=template_id,
        name=request_body.name,
        content=request_body.content,
        category=request_body.category,
        tags=request_body.tags,
        variables=request_body.variables,
        version=request_body.version,
        created_at=existing.created_at,
        updated_at=datetime.now(timezone.utc),
        metadata=request_body.metadata,
    )

    saved_id = storage.save_template(template)
    template.id = saved_id or template_id
    return template_to_response(template)


@router.get("/templates/{template_id}", response_model=PromptTemplateResponse)
async def get_template(
    template_id: int,
    storage: Storage = Depends(get_storage),
) -> PromptTemplateResponse:
    template = storage.get_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="模板不存在")
    return template_to_response(template)


@router.get("/templates/", response_model=List[PromptTemplateResponse])
async def list_templates(
    storage: Storage = Depends(get_storage),
) -> List[PromptTemplateResponse]:
    return [template_to_response(t) for t in storage.list_templates()]


@router.delete("/templates/{template_id}")
async def delete_template(
    template_id: int,
    storage: Storage = Depends(get_storage),
) -> dict:
    deleted = storage.delete_template(template_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="模板不存在")
    return {"message": "模板已删除"}


@router.post("/render/", response_model=RenderTemplateResponse)
async def render_template(
    request_body: RenderTemplateRequest,
    storage: Storage = Depends(get_storage),
) -> RenderTemplateResponse:
    template = storage.get_template(request_body.template_id)
    if not template:
        raise HTTPException(status_code=404, detail="模板不存在")

    rendered = PromptEngine.render_template(template, request_body.context)
    return RenderTemplateResponse(rendered=rendered)


@router.post("/evaluate/", response_model=TestResultResponse)
async def evaluate_prompt(
    request_body: EvaluatePromptRequest,
    storage: Storage = Depends(get_storage),
) -> TestResultResponse:
    template = storage.get_template(request_body.template_id)
    if not template:
        raise HTTPException(status_code=404, detail="模板不存在")

    try:
        result = PromptEngine.evaluate_prompt(
            template=template,
            input_data=request_body.input_data,
            model_name=request_body.model_name,
        )
        result.id = storage.save_test_result(result)
        return test_result_to_response(result)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"评估失败：{str(exc)}")


@router.post("/optimize/", response_model=PromptTemplateResponse)
async def optimize_prompt(
    request_body: OptimizePromptRequest,
    storage: Storage = Depends(get_storage),
) -> PromptTemplateResponse:
    template = storage.get_template(request_body.template_id)
    if not template:
        raise HTTPException(status_code=404, detail="模板不存在")

    optimized = PromptEngine.optimize_prompt(template)
    optimized.id = storage.save_template(optimized)
    return template_to_response(optimized)


@router.post("/variants/", response_model=List[PromptTemplateResponse])
async def generate_variants(
    request_body: GenerateVariantsRequest,
    storage: Storage = Depends(get_storage),
) -> List[PromptTemplateResponse]:
    template = storage.get_template(request_body.template_id)
    if not template:
        raise HTTPException(status_code=404, detail="模板不存在")

    variants = PromptEngine.generate_variants(template)
    return [template_to_response(v) for v in variants]


@router.get("/analytics/", response_model=AnalyticsResponse)
async def get_analytics(
    storage: Storage = Depends(get_storage),
) -> AnalyticsResponse:
    return AnalyticsResponse(**storage.get_analytics())


@router.get("/settings/provider", response_model=AIProviderSettingsResponse)
async def get_provider_settings() -> AIProviderSettingsResponse:
    config = read_provider_config()
    return public_provider_config(config)


@router.post("/settings/provider", response_model=AIProviderSettingsResponse)
async def save_provider_settings(
    request_body: AIProviderSettingsRequest,
) -> AIProviderSettingsResponse:
    current = read_provider_config()
    incoming = model_dump_compat(request_body, exclude_none=True)

    provider = incoming.get("provider") or current.get("provider") or "openai"
    model = incoming.get("model") or current.get("model") or DEFAULT_PROVIDER_CONFIG["model"]

    api_key = incoming.get("api_key")
    if api_key is None or not str(api_key).strip() or "..." in str(api_key):
        api_key = current.get("api_key") or ""
    else:
        api_key = str(api_key).strip()

    api_base = incoming.get("api_base")
    if api_base is None or not str(api_base).strip():
        api_base = DEFAULT_API_BASES.get(provider, "")
    else:
        api_base = str(api_base).strip().rstrip("/")

    config = {
        "provider": provider,
        "api_key": api_key,
        "model": model,
        "api_base": api_base,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    write_provider_config(config)
    return public_provider_config(config)


@router.post("/chat/", response_model=ChatResponse)
async def chat_with_provider(
    request_body: ChatRequest,
    storage: Storage = Depends(get_storage),
) -> ChatResponse:
    template = storage.get_template(request_body.template_id)
    if not template:
        raise HTTPException(status_code=404, detail="模板不存在")

    config = read_provider_config()

    if request_body.provider:
        config["provider"] = request_body.provider
        if not config.get("api_base"):
            config["api_base"] = DEFAULT_API_BASES.get(request_body.provider, "")

    rendered = PromptEngine.render_template(template, request_body.context or {})

    start = time.perf_counter()
    provider_result = await call_ai_provider(config, rendered)
    latency_ms = int((time.perf_counter() - start) * 1000)

    ai_response = provider_result["response"]
    token_usage = int(provider_result.get("token_usage") or 0)
    provider_name = config.get("provider") or "openai"
    model_name = config.get("model") or ""

    try:
        test_result = TestResult(
            id=0,
            template_id=template.id,
            model_name=model_name,
            input_prompt=rendered,
            output_response=ai_response,
            score=0,
            latency_ms=latency_ms,
            token_usage=token_usage,
            created_at=datetime.now(timezone.utc),
        )
        storage.save_test_result(test_result)
    except Exception:
        pass

    return ChatResponse(
        template_id=template.id,
        rendered=rendered,
        response=ai_response,
        provider=provider_name,
        model=model_name,
        latency_ms=latency_ms,
        token_usage=token_usage,
        raw_response=provider_result.get("raw_response"),
    )