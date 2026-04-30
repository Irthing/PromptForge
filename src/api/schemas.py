from pydantic import BaseModel
from typing import List, Optional, Dict


class PromptTemplateSchema(BaseModel):
    id: int
    name: str
    content: str
    category: str
    tags: List[str]
    variables: List[str]
    version: str
    created_at: str
    updated_at: str
    metadata: Optional[dict]


class TestResultSchema(BaseModel):
    id: int
    template_id: int
    model_name: str
    input_prompt: str
    output_response: str
    score: float
    latency_ms: int
    token_usage: int
    created_at: str


class CreateTemplateRequest(BaseModel):
    name: str
    content: str
    category: str
    tags: List[str]
    variables: List[str]
    version: str


class RenderTemplateRequest(BaseModel):
    context: Dict[str, str]


class EvaluatePromptRequest(BaseModel):
    input_data: Dict[str, str]
    model_name: str


class OptimizePromptRequest(BaseModel):
    pass


class GenerateVariantsRequest(BaseModel):
    pass


class AnalyticsResponse(BaseModel):
    templates_count: int
    test_results_count: int
