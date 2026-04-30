from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime


@dataclass
class PromptTemplate:
    id: int
    name: str
    content: str
    category: str
    tags: List[str]
    variables: List[str]
    version: str
    created_at: datetime
    updated_at: datetime
    metadata: Optional[dict]


@dataclass
class PromptVersion:
    version_number: str
    template_id: int
    content: str
    changelog: str
    created_at: datetime


@dataclass
class TestResult:
    id: int
    template_id: int
    model_name: str
    input_prompt: str
    output_response: str
    score: float
    latency_ms: int
    token_usage: int
    created_at: datetime


@dataclass
class Tag:
    name: str
    color: str
    description: str


@dataclass
class Category:
    name: str
    description: str
    icon: str
