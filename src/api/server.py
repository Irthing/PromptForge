from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from .storage import Storage
from .models import PromptTemplate, TestResult
from .engine import PromptEngine
from typing import List, Dict


app = FastAPI()

origins = [
    "http://localhost",
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

storage = Storage()


@app.post("/templates/")
async def create_template(template: PromptTemplate):
    storage.save_template(template)
    return template


@app.get("/templates/{template_id}")
async def get_template(template_id: int):
    template = storage.get_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return template


@app.get("/templates/")
async def list_templates() -> List[PromptTemplate]:
    return storage.list_templates()


@app.delete("/templates/{template_id}")
async def delete_template(template_id: int):
    storage.delete_template(template_id)
    return {"message": "Template deleted successfully"}


@app.post("/render/")
async def render_template(template_id: int, context: Dict[str, str]):
    template = storage.get_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    rendered = PromptEngine.render_template(template, context)
    return {"rendered": rendered}


@app.post("/evaluate/")
async def evaluate_prompt(template_id: int, input_data: Dict[str, str], model_name: str):
    template = storage.get_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    result = PromptEngine.evaluate_prompt(template, input_data, model_name)
    storage.save_test_result(result)
    return result


@app.post("/optimize/")
async def optimize_prompt(template_id: int):
    template = storage.get_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    optimized_template = PromptEngine.optimize_prompt(template)
    storage.save_template(optimized_template)
    return optimized_template


@app.post("/variants/")
async def generate_variants(template_id: int):
    template = storage.get_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    variants = PromptEngine.generate_variants(template)
    return variants


@app.get("/analytics/")
async def get_analytics():
    analytics = storage.get_analytics()
    return analytics
