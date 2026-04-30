from datetime import datetime, timezone
import time
from typing import List

from jinja2 import Environment, Template, meta, TemplateSyntaxError

from .models import PromptTemplate, TestResult


class PromptEngine:

    @staticmethod
    def render_template(prompt: PromptTemplate, context: dict) -> str:
        template = Template(prompt.content)
        return template.render(context or {})

    @staticmethod
    def evaluate_prompt(
        prompt: PromptTemplate,
        input_data: dict,
        model_name: str,
    ) -> TestResult:
        start_time = time.time()
        output_response = PromptEngine.render_template(prompt, input_data)
        latency_ms = (time.time() - start_time) * 1000

        return TestResult(
            id=0,
            template_id=prompt.id,
            model_name=model_name,
            input_prompt=str(input_data),
            output_response=output_response,
            score=0,
            latency_ms=int(latency_ms),
            token_usage=len(output_response.split()),
            created_at=datetime.now(timezone.utc),
        )

    @staticmethod
    def optimize_prompt(prompt: PromptTemplate) -> PromptTemplate:
        optimized_content = prompt.content.replace("  ", " ").strip()

        return PromptTemplate(
            id=prompt.id,
            name=prompt.name,
            content=optimized_content,
            category=prompt.category,
            tags=list(prompt.tags or []),
            variables=list(prompt.variables or []),
            version=prompt.version,
            created_at=prompt.created_at,
            updated_at=datetime.now(timezone.utc),
            metadata=dict(prompt.metadata or {}),
        )

    @staticmethod
    def generate_variants(prompt: PromptTemplate) -> List[PromptTemplate]:
        return [prompt]

    @staticmethod
    def extract_variables(prompt: PromptTemplate) -> List[str]:
        environment = Environment()
        ast = environment.parse(prompt.content)
        return sorted(meta.find_undeclared_variables(ast))

    @staticmethod
    def validate_template(prompt: PromptTemplate) -> bool:
        if not prompt.content or not prompt.name:
            return False

        try:
            PromptEngine.extract_variables(prompt)
        except TemplateSyntaxError:
            return False

        return True
