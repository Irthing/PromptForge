from datetime import datetime
from typing import Any, Dict, List

from pydantic import BaseModel, Field

from ..core.models import PromptTemplate, TestResult


class CreateTemplateRequest(BaseModel):
    name: str
    content: str
    category: str = ""
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
    model_name: str


class OptimizePromptRequest(BaseModel):
    template_id: int


class GenerateVariantsRequest(BaseModel):
    template_id: int


class PromptTemplateResponse(BaseModel):
    id: int
    name: str
    content: str
    category: str
    tags: List[str]
    variables: List[str]
    version: str
    created_at: datetime
    updated_at: datetime
    metadata: Dict[str, Any]


class TestResultResponse(BaseModel):
    id: int
    template_id: int
    model_name: str
    input_prompt: str
    output_response: str
    score: float
    latency_ms: int
    token_usage: int
    created_at: datetime


class AnalyticsResponse(BaseModel):
    templates_count: int
    test_results_count: int


def template_to_response(template: PromptTemplate) -> PromptTemplateResponse:
    return PromptTemplateResponse(
        id=template.id,
        name=template.name,
        content=template.content,
        category=template.category,
        tags=list(template.tags or []),
        variables=list(template.variables or []),
        version=template.version,
        created_at=template.created_at,
        updated_at=template.updated_at,
        metadata=dict(template.metadata or {}),
    )


def test_result_to_response(result: TestResult) -> TestResultResponse:
    return TestResultResponse(
        id=result.id,
        template_id=result.template_id,
        model_name=result.model_name,
        input_prompt=result.input_prompt,
        output_response=result.output_response,
        score=result.score,
        latency_ms=result.latency_ms,
        token_usage=result.token_usage,
        created_at=result.created_at,
    )
