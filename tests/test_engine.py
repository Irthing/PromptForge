# tests/test_engine.py

from datetime import datetime, timezone

import pytest

from src.core.engine import PromptEngine
from src.core.models import PromptTemplate, TestResult


@pytest.fixture
def prompt_template() -> PromptTemplate:
    """Return a reusable prompt template fixture."""
    now = datetime.now(timezone.utc)
    return PromptTemplate(
        id=1,
        name="Greeting Template",
        content="Hello {{ name }}, your role is {{ role }}.",
        category="General",
        tags=["greeting", "role"],
        variables=["name", "role"],
        version="1.0.0",
        created_at=now,
        updated_at=now,
        metadata={"owner": "tests"},
    )


@pytest.mark.parametrize(
    ("context", "expected"),
    [
        ({"name": "Ada", "role": "engineer"}, "Hello Ada, your role is engineer."),
        ({"name": "Grace", "role": "researcher"}, "Hello Grace, your role is researcher."),
    ],
)
def test_render_template(prompt_template: PromptTemplate, context: dict, expected: str) -> None:
    """PromptEngine renders Jinja2 variables using the supplied context."""
    rendered = PromptEngine.render_template(prompt_template, context)
    assert rendered == expected


@pytest.mark.parametrize(
    ("content", "expected"),
    [
        ("Write about {{ topic }} for {{ audience }}.", ["topic", "audience"]),
        ("{{ greeting }}, {{ name }}! {{ greeting }}, {{ name }}!", ["greeting", "name"]),
        ("No variables here.", []),
    ],
)
def test_extract_variables(content: str, expected: list[str]) -> None:
    """extract_variables correctly identifies Jinja2 placeholder names."""
    template = PromptTemplate(
        id=1,
        name="test",
        content=content,
        category="test",
        tags=[],
        variables=[],
        version="1.0.0",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        metadata={},
    )
    result = PromptEngine.extract_variables(template)
    assert set(result) == set(expected)


@pytest.mark.parametrize(
    ("name", "content", "expected_valid"),
    [
        ("Valid", "Some content", True),
        ("", "Some content", False),
        ("Valid", "", False),
        ("", "", False),
    ],
)
def test_validate_template(name: str, content: str, expected_valid: bool) -> None:
    """validate_template returns True when both name and content are non-empty."""
    template = PromptTemplate(
        id=1,
        name=name,
        content=content,
        category="test",
        tags=[],
        variables=[],
        version="1.0.0",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        metadata={},
    )
    assert PromptEngine.validate_template(template) == expected_valid


def test_evaluate_prompt(prompt_template: PromptTemplate) -> None:
    """evaluate_prompt returns a TestResult with sensible defaults."""
    result = PromptEngine.evaluate_prompt(
        prompt_template,
        input_data={"name": "Test", "role": "dev"},
        model_name="test-model",
    )
    assert isinstance(result, TestResult)
    assert result.template_id == prompt_template.id
    assert result.model_name == "test-model"
    assert result.latency_ms >= 0
    assert result.token_usage > 0
