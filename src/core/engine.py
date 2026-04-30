from jinja2 import Template
from typing import List
from .models import PromptTemplate, TestResult
import time


class PromptEngine:

    @staticmethod
    def render_template(prompt: PromptTemplate, context: dict) -> str:
        template = Template(prompt.content)
        return template.render(context)

    @staticmethod
    def evaluate_prompt(prompt: PromptTemplate, input_data: dict, model_name: str) -> TestResult:
        start_time = time.time()
        output_response = PromptEngine.render_template(prompt, input_data)
        latency_ms = (time.time() - start_time) * 1000
        score = 0  # Placeholder: Score calculation logic based on model output

        return TestResult(
            id=0,  # Auto-generated ID
            template_id=prompt.id,
            model_name=model_name,
            input_prompt=str(input_data),
            output_response=output_response,
            score=score,
            latency_ms=int(latency_ms),
            token_usage=len(output_response.split()),
            created_at=time.time()
        )

    @staticmethod
    def optimize_prompt(prompt: PromptTemplate) -> PromptTemplate:
        # Placeholder logic for optimization
        optimized_content = prompt.content.replace("  ", " ").strip()  # Basic optimization
        return PromptTemplate(
            id=prompt.id,
            name=prompt.name,
            content=optimized_content,
            category=prompt.category,
            tags=prompt.tags,
            variables=prompt.variables,
            version=prompt.version,
            created_at=prompt.created_at,
            updated_at=time.time(),
            metadata=prompt.metadata
        )

    @staticmethod
    def generate_variants(prompt: PromptTemplate) -> List[PromptTemplate]:
        # Placeholder: Generate variants by altering prompt structure
        variants = [prompt]  # For now, just return the original template
        return variants

    @staticmethod
    def extract_variables(prompt: PromptTemplate) -> List[str]:
        template = Template(prompt.content)
        # Extract variables based on Jinja2 syntax {{ variable }}
        return [var.strip() for var in template._parse(prompt.content)[1] if isinstance(var, str)]

    @staticmethod
    def validate_template(prompt: PromptTemplate) -> bool:
        if not prompt.content or not prompt.name:
            return False
        return True
