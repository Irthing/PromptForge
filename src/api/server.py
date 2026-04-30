from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request

from ..core.engine import PromptEngine
from ..core.models import PromptTemplate
from ..core.storage import Storage
from .schemas import (
    AnalyticsResponse,
    CreateTemplateRequest,
    EvaluatePromptRequest,
    GenerateVariantsRequest,
    OptimizePromptRequest,
    PromptTemplateResponse,
    RenderTemplateRequest,
    RenderTemplateResponse,
    TestResultResponse,
    template_to_response,
    test_result_to_response,
)


router = APIRouter()


def get_storage(request: Request) -> Storage:
    storage = getattr(request.app.state, "storage", None)
    if storage is None:
        raise HTTPException(status_code=500, detail="Storage is not initialized")
    return storage


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


@router.get("/templates/{template_id}", response_model=PromptTemplateResponse)
async def get_template(
    template_id: int,
    storage: Storage = Depends(get_storage),
) -> PromptTemplateResponse:
    template = storage.get_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
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
        raise HTTPException(status_code=404, detail="Template not found")
    return {"message": "Template deleted successfully"}


@router.post("/render/", response_model=RenderTemplateResponse)
async def render_template(
    request_body: RenderTemplateRequest,
    storage: Storage = Depends(get_storage),
) -> RenderTemplateResponse:
    template = storage.get_template(request_body.template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    rendered = PromptEngine.render_template(template, request_body.context)
    return RenderTemplateResponse(rendered=rendered)


@router.post("/evaluate/", response_model=TestResultResponse)
async def evaluate_prompt(
    request_body: EvaluatePromptRequest,
    storage: Storage = Depends(get_storage),
) -> TestResultResponse:
    template = storage.get_template(request_body.template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    result = PromptEngine.evaluate_prompt(
        template=template,
        input_data=request_body.input_data,
        model_name=request_body.model_name,
    )
    result.id = storage.save_test_result(result)
    return test_result_to_response(result)


@router.post("/optimize/", response_model=PromptTemplateResponse)
async def optimize_prompt(
    request_body: OptimizePromptRequest,
    storage: Storage = Depends(get_storage),
) -> PromptTemplateResponse:
    template = storage.get_template(request_body.template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
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
        raise HTTPException(status_code=404, detail="Template not found")
    variants = PromptEngine.generate_variants(template)
    return [template_to_response(v) for v in variants]


@router.get("/analytics/", response_model=AnalyticsResponse)
async def get_analytics(
    storage: Storage = Depends(get_storage),
) -> AnalyticsResponse:
    return AnalyticsResponse(**storage.get_analytics())
