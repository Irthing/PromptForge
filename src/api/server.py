"""PromptForge API server - template management, AI provider settings, chat."""
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
PROVIDER_CONFIG_PATH = Path(os.getenv("PROMPTFORGE_PROVIDER_CONFIG", "provider_config.json"))
ALLOWED_PROVIDERS = {"openai", "anthropic", "custom"}
ALLOWED_REASONING = {"low", "medium", "high"}

DEFAULT_API_BASES: Dict[str, str] = {
    "openai": "https://api.openai.com/v1",
    "anthropic": "https://api.anthropic.com/v1",
    "custom": "",
}

# Default configuration for the AI provider.
#
# The temperature controls the randomness of generated content. A lower value
# results in more deterministic outputs, while higher values yield more
# varied responses. Historically this project defaulted to 1.0, but it has
# been updated to a saner default of 0.7 to balance creativity and
# determinism. Similarly, the default `max_tokens` has been raised from
# 4096 to 8192 so that longer outputs can be generated without users
# needing to adjust the setting manually. These values are also used as
# fall‑backs throughout the application and are clamped to sensible
# ranges in the `_norm` helper below.
DEFAULT_PROVIDER_CONFIG: Dict[str, Any] = {
    "provider": "openai",
    "api_key": "",
    "model": "gpt-4o-mini",
    "api_base": "https://api.openai.com/v1",
    # Updated defaults: temperature now defaults to 0.7 instead of 1.0
    "temperature": 0.7,
    # Allow more tokens by default. Previously 4096, now 8192.
    "max_tokens": 8192,
    "reasoning_effort": "medium",
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


def _clamp(value: Any, default: float, lo: float, hi: float) -> float:
    try:
        v = float(value)
    except (TypeError, ValueError):
        return default
    return max(lo, min(hi, v))


def _norm(config: Dict[str, Any]) -> Dict[str, Any]:
    n = DEFAULT_PROVIDER_CONFIG.copy()
    n.update({k: v for k, v in config.items() if v is not None})
    p = str(n.get("provider") or "openai")
    if p not in ALLOWED_PROVIDERS:
        p = "openai"
    n["provider"] = p
    n["api_key"] = str(n.get("api_key") or "")
    n["model"] = str(n.get("model") or DEFAULT_PROVIDER_CONFIG["model"])
    base = str(n.get("api_base") or "").strip().rstrip("/")
    n["api_base"] = base or DEFAULT_API_BASES.get(p, "")
    # Clamp temperature around the updated default of 0.7 and ensure it
    # stays within [0, 2]. If the provided value is invalid or None,
    # `_clamp` will fall back to 0.7.
    n["temperature"] = _clamp(n.get("temperature"), 0.7, 0, 2)
    # Clamp max_tokens around the new default of 8192.  The upper bound
    # has been increased to 200000 to accommodate models that support
    # longer outputs.  Invalid or missing values fall back to 8192.
    n["max_tokens"] = int(_clamp(n.get("max_tokens"), 8192, 1, 200000))
    r = str(n.get("reasoning_effort") or "medium")
    if r not in ALLOWED_REASONING:
        r = "medium"
    n["reasoning_effort"] = r
    return n


def read_config() -> Dict[str, Any]:
    if not PROVIDER_CONFIG_PATH.exists():
        return DEFAULT_PROVIDER_CONFIG.copy()
    try:
        with PROVIDER_CONFIG_PATH.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return DEFAULT_PROVIDER_CONFIG.copy()
        return _norm(data)
    except (OSError, json.JSONDecodeError):
        return DEFAULT_PROVIDER_CONFIG.copy()


def write_config(config: Dict[str, Any]) -> None:
    n = _norm(config)
    with PROVIDER_CONFIG_PATH.open("w", encoding="utf-8") as f:
        json.dump(n, f, ensure_ascii=False, indent=2)


def mask_key(key: Optional[str]) -> str:
    if not key or len(key) <= 8:
        return "****"
    return f"{key[:4]}...{key[-4:]}"


def pub_config(config: Dict[str, Any]) -> AIProviderSettingsResponse:
    return AIProviderSettingsResponse(
        provider=config["provider"],
        model=config["model"],
        api_base=config["api_base"],
        api_key=mask_key(config.get("api_key")),
        configured=bool(config.get("api_key")),
        temperature=config["temperature"],
        max_tokens=config["max_tokens"],
        reasoning_effort=config["reasoning_effort"],
    )


# ====== Template CRUD ======

@router.post("/templates/", response_model=PromptTemplateResponse)
async def create_template(
    body: CreateTemplateRequest, storage: Storage = Depends(get_storage),
) -> PromptTemplateResponse:
    now = datetime.now(timezone.utc)
    t = PromptTemplate(
        id=0,
        name=body.name,
        content=body.content,
        category=body.category,
        tags=body.tags,
        variables=body.variables,
        version=body.version,
        created_at=now,
        updated_at=now,
        metadata=body.metadata,
    )
    t.id = storage.save_template(t)
    return template_to_response(t)


@router.put("/templates/{tid}", response_model=PromptTemplateResponse)
async def update_template(
    tid: int, body: UpdateTemplateRequest, storage: Storage = Depends(get_storage),
) -> PromptTemplateResponse:
    old = storage.get_template(tid)
    if not old:
        raise HTTPException(404, "模板不存在")
    now = datetime.now(timezone.utc)
    t = PromptTemplate(
        id=tid,
        name=body.name,
        content=body.content,
        category=body.category,
        tags=body.tags,
        variables=body.variables,
        version=body.version,
        created_at=old.created_at,
        updated_at=now,
        metadata=body.metadata,
    )
    storage.save_template(t)
    return template_to_response(t)


@router.get("/templates/{tid}", response_model=PromptTemplateResponse)
async def get_template(tid: int, storage: Storage = Depends(get_storage)) -> PromptTemplateResponse:
    t = storage.get_template(tid)
    if not t:
        raise HTTPException(404, "模板不存在")
    return template_to_response(t)


@router.get("/templates/", response_model=List[PromptTemplateResponse])
async def list_templates(storage: Storage = Depends(get_storage)) -> List[PromptTemplateResponse]:
    return [template_to_response(t) for t in storage.list_templates()]


@router.delete("/templates/{tid}")
async def delete_template(tid: int, storage: Storage = Depends(get_storage)) -> dict:
    if not storage.delete_template(tid):
        raise HTTPException(404, "模板不存在")
    return {"message": "模板已删除"}


# ====== Render / Evaluate / Optimize ======

@router.post("/render/", response_model=RenderTemplateResponse)
async def render_template(
    body: RenderTemplateRequest, storage: Storage = Depends(get_storage),
) -> RenderTemplateResponse:
    t = storage.get_template(body.template_id)
    if not t:
        raise HTTPException(404, "模板不存在")
    return RenderTemplateResponse(rendered=PromptEngine.render_template(t, body.context))


@router.post("/evaluate/", response_model=TestResultResponse)
async def evaluate_prompt(
    body: EvaluatePromptRequest, storage: Storage = Depends(get_storage),
) -> TestResultResponse:
    t = storage.get_template(body.template_id)
    if not t:
        raise HTTPException(404, "模板不存在")
    try:
        result = PromptEngine.evaluate_prompt(t, body.input_data, body.model_name)
        result.id = storage.save_test_result(result)
        return test_result_to_response(result)
    except Exception as e:
        raise HTTPException(500, f"评估失败: {e}")


@router.post("/optimize/", response_model=PromptTemplateResponse)
async def optimize_prompt(
    body: OptimizePromptRequest, storage: Storage = Depends(get_storage),
) -> PromptTemplateResponse:
    t = storage.get_template(body.template_id)
    if not t:
        raise HTTPException(404, "模板不存在")
    opt = PromptEngine.optimize_prompt(t)
    opt.id = storage.save_template(opt)
    return template_to_response(opt)


@router.post("/variants/", response_model=List[PromptTemplateResponse])
async def generate_variants(
    body: GenerateVariantsRequest, storage: Storage = Depends(get_storage),
) -> List[PromptTemplateResponse]:
    t = storage.get_template(body.template_id)
    if not t:
        raise HTTPException(404, "模板不存在")
    return [template_to_response(v) for v in PromptEngine.generate_variants(t)]


@router.get("/analytics/", response_model=AnalyticsResponse)
async def get_analytics(storage: Storage = Depends(get_storage)) -> AnalyticsResponse:
    return AnalyticsResponse(**storage.get_analytics())


# ====== AI Provider Settings ======

@router.get("/settings/provider", response_model=AIProviderSettingsResponse)
async def get_provider_settings() -> AIProviderSettingsResponse:
    return pub_config(read_config())


@router.post("/settings/provider", response_model=AIProviderSettingsResponse)
async def save_provider_settings(
    body: AIProviderSettingsRequest,
) -> AIProviderSettingsResponse:
    current = read_config()
    inc = model_dump_compat(body, exclude_none=True)
    api_key = inc.get("api_key")
    if api_key is None or not str(api_key).strip() or "..." in str(api_key):
        api_key = current.get("api_key", "")
    else:
        api_key = str(api_key).strip()
    config = _norm({
        "provider": inc.get("provider", current.get("provider", "openai")),
        "api_key": api_key,
        "model": inc.get("model", current.get("model", "gpt-4o-mini")),
        "api_base": inc.get("api_base", current.get("api_base", "")),
        # Use 0.7 as the fallback if the incoming temperature is None or invalid
        "temperature": inc.get("temperature", current.get("temperature", 0.7)),
        # Use 8192 as the fallback for max_tokens instead of 4096
        "max_tokens": inc.get("max_tokens", current.get("max_tokens", 8192)),
        "reasoning_effort": inc.get("reasoning_effort", current.get("reasoning_effort", "medium")),
    })
    write_config(config)
    return pub_config(config)


# ====== AI Chat ======

async def _call_ai(config: Dict[str, Any], prompt: str) -> Dict[str, Any]:
    p = config["provider"]
    key = config["api_key"]
    model = config["model"]
    base = config["api_base"]
    temp = config["temperature"]
    max_tk = config["max_tokens"]
    effort = config["reasoning_effort"]

    if not key:
        raise HTTPException(400, "请先保存 API 密钥")
    if not model:
        raise HTTPException(400, "请先填写模型名称")

    if p == "anthropic":
        url = (base or DEFAULT_API_BASES["anthropic"]).rstrip("/") + "/messages"
        headers = {
            "x-api-key": key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }
        body = {
            "model": model,
            "max_tokens": max_tk,
            "temperature": temp,
            "messages": [{"role": "user", "content": prompt}],
        }
    else:
        url = (base or DEFAULT_API_BASES.get(p, "")).rstrip("/")
        if not url.endswith("/chat/completions"):
            url += "/chat/completions"
        headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
        body = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temp,
            "max_tokens": max_tk,
            "reasoning_effort": effort,
        }

    async with httpx.AsyncClient(timeout=90) as client:
        r = await client.post(url, headers=headers, json=body)

    if r.status_code >= 400:
        detail = r.text[:200]
        raise HTTPException(502, f"AI 调用失败: {detail}")

    data = r.json()
    if p == "anthropic":
        parts = []
        for block in (data.get("content") or []):
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(str(block.get("text", "")))
            elif isinstance(block, str):
                parts.append(block)
        response_text = "\n".join(p for p in parts if p)
        usage = data.get("usage") or {}
        tokens = int(usage.get("input_tokens", 0)) + int(usage.get("output_tokens", 0))
    else:
        choice = (data.get("choices") or [{}])[0]
        msg = choice.get("message") or {}
        response_text = msg.get("content") or choice.get("text") or ""
        usg = data.get("usage") or {}
        tokens = int(usg.get("total_tokens") or usg.get("completion_tokens") or 0)

    return {
        "response": response_text,
        "token_usage": tokens,
        "raw_response": data,
    }


@router.post("/chat/", response_model=ChatResponse)
async def chat_with_provider(
    body: ChatRequest, storage: Storage = Depends(get_storage),
) -> ChatResponse:
    t = storage.get_template(body.template_id)
    if not t:
        raise HTTPException(404, "模板不存在")
    config = read_config()
    if body.provider:
        config["provider"] = body.provider
    config = _norm(config)
    rendered = PromptEngine.render_template(t, body.context or {})
    start = time.perf_counter()
    result = await _call_ai(config, rendered)
    latency = int((time.perf_counter() - start) * 1000)
    try:
        tr = TestResult(
            id=0,
            template_id=t.id,
            model_name=config["model"],
            input_prompt=rendered,
            output_response=result["response"],
            score=0,
            latency_ms=latency,
            token_usage=int(result.get("token_usage", 0)),
            created_at=datetime.now(timezone.utc),
        )
        tr.id = storage.save_test_result(tr)
    except Exception:
        pass
    return ChatResponse(
        template_id=t.id,
        rendered=rendered,
        response=result["response"],
        provider=config["provider"],
        model=config["model"],
        latency_ms=latency,
        token_usage=int(result.get("token_usage", 0)),
        raw_response=result.get("raw_response"),
    )
