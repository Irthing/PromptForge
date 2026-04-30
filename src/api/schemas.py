from __future__ import annotations
import json
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field

AIProviderName = Literal["openai", "anthropic", "custom"]
ReasoningEffort = Literal["low", "medium", "high"]


class CreateTemplateRequest(BaseModel):
    name: str
    content: str
    category: str = "未分类"
    tags: List[str] = Field(default_factory=list)
    variables: List[str] = Field(default_factory=list)
    version: str = "1.0"
    metadata: Dict[str, Any] = Field(default_factory=dict)


class UpdateTemplateRequest(BaseModel):
    name: str
    content: str
    category: str = "未分类"
    tags: List[str] = Field(default_factory=list)
    variables: List[str] = Field(default_factory=list)
    version: str = "1.0"
    metadata: Dict[str, Any] = Field(default_factory=dict)


class RenderTemplateRequest(BaseModel):
    template_id: int
    context: Dict[str, Any] = Field(default_factory=dict)


class RenderTemplateResponse(BaseModel):
    rendered: str


class EvaluatePromptRequest(BaseModel):
    template_id: int
    input_data: Dict[str, Any] = Field(default_factory=dict)
    model_name: str = "本地评估"


class OptimizePromptRequest(BaseModel):
    template_id: int


class GenerateVariantsRequest(BaseModel):
    template_id: int


class PromptTemplateResponse(BaseModel):
    id: int
    name: str
    content: str
    category: str
    tags: List[str] = Field(default_factory=list)
    variables: List[str] = Field(default_factory=list)
    version: str
    created_at: datetime
    updated_at: datetime
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TestResultResponse(BaseModel):
    id: int
    template_id: int
    model_name: str
    input_prompt: str
    output_response: str
    score: float = 0
    latency_ms: int = 0
    token_usage: int = 0
    created_at: datetime


class AnalyticsResponse(BaseModel):
    templates_count: int = 0
    test_results_count: int = 0
    average_score: float = 0


class AIProviderSettingsRequest(BaseModel):
    provider: AIProviderName = "openai"
    api_key: Optional[str] = None
    model: str = "gpt-4o-mini"
    api_base: Optional[str] = None
    # Temperature defaults to 0.7 instead of 1.0. Accept values between 0 and 2.
    temperature: float = Field(default=0.7, ge=0, le=2)
    # Increase the default max_tokens from 4096 to 8192 and raise the upper bound
    # to 200000 to support models with very large context windows.
    max_tokens: int = Field(default=8192, ge=1, le=200000)
    reasoning_effort: ReasoningEffort = "medium"


class AIProviderSettingsResponse(BaseModel):
    provider: AIProviderName = "openai"
    api_key: str = ""
    model: str = "gpt-4o-mini"
    api_base: str = "https://api.openai.com/v1"
    configured: bool = False
    # Reflect updated defaults in the response: temperature=0.7, max_tokens=8192
    temperature: float = 0.7
    max_tokens: int = 8192
    reasoning_effort: ReasoningEffort = "medium"


class ChatRequest(BaseModel):
    template_id: int
    context: Dict[str, Any] = Field(default_factory=dict)
    provider: Optional[AIProviderName] = None


class ChatResponse(BaseModel):
    template_id: int
    rendered: str
    response: str
    provider: str
    model: str
    latency_ms: int
    token_usage: int = 0
    raw_response: Optional[Any] = None


def ensure_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    return [str(value).strip()] if str(value).strip() else []


def ensure_metadata(value: Any) -> Dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return {}
        try:
            parsed = json.loads(text)
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}
    return {}


def template_to_response(template: Any) -> PromptTemplateResponse:
    return PromptTemplateResponse(
        id=template.id,
        name=template.name,
        content=template.content,
        category=template.category,
        tags=ensure_list(template.tags),
        variables=ensure_list(template.variables),
        version=template.version,
        created_at=template.created_at,
        updated_at=template.updated_at,
        metadata=ensure_metadata(template.metadata),
    )


def test_result_to_response(result: Any) -> TestResultResponse:
    return TestResultResponse(
        id=result.id,
        template_id=result.template_id,
        model_name=result.model_name,
        input_prompt=result.input_prompt,
        output_response=result.output_response,
        score=float(result.score or 0),
        latency_ms=int(result.latency_ms or 0),
        token_usage=int(result.token_usage or 0),
        created_at=result.created_at,
    )