# tests/test_storage.py

from datetime import datetime, timezone

import pytest

from src.core.models import PromptTemplate, PromptVersion
from src.core.storage import Storage


@pytest.fixture
def storage(tmp_path):
    """Create a Storage instance backed by a temporary database."""
    db_path = tmp_path / "test_promptforge.db"
    return Storage(db_path=str(db_path))


@pytest.fixture
def sample_template() -> PromptTemplate:
    """Return a sample PromptTemplate for testing."""
    now = datetime.now(timezone.utc)
    return PromptTemplate(
        id=0,
        name="Test Template",
        content="Hello {{ name }}",
        category="Testing",
        tags=["test", "sample"],
        variables=["name"],
        version="1.0.0",
        created_at=now,
        updated_at=now,
        metadata={"source": "pytest"},
    )


def test_save_and_get_template(storage: Storage, sample_template: PromptTemplate) -> None:
    """save_template persists a template; get_template retrieves it."""
    tid = storage.save_template(sample_template)
    retrieved = storage.get_template(tid)
    assert retrieved is not None
    assert retrieved.name == sample_template.name
    assert retrieved.content == sample_template.content


def test_list_templates(storage: Storage, sample_template: PromptTemplate) -> None:
    """list_templates returns all saved templates."""
    assert len(storage.list_templates()) == 0
    storage.save_template(sample_template)
    templates = storage.list_templates()
    assert len(templates) == 1
    assert templates[0].name == "Test Template"


def test_delete_template(storage: Storage, sample_template: PromptTemplate) -> None:
    """delete_template removes a template from the database."""
    storage.save_template(sample_template)
    assert len(storage.list_templates()) == 1
    tid = storage.save_template(sample_template)
    storage.delete_template(tid)
    assert len(storage.list_templates()) == 1  # first save still there
    # Clean up
    all_templates = storage.list_templates()
    for t in all_templates:
        storage.delete_template(t.id)
    assert len(storage.list_templates()) == 0


def test_search_templates(storage: Storage, sample_template: PromptTemplate) -> None:
    """search_templates finds templates matching a full-text query."""
    storage.save_template(sample_template)
    results = storage.search_templates("Hello")
    assert len(results) >= 1


def test_save_version(storage: Storage, sample_template: PromptTemplate) -> None:
    """save_version persists a version entry linked to a template."""
    tid = storage.save_template(sample_template)
    now = datetime.now(timezone.utc)
    version = PromptVersion(
        version_number="2.0.0",
        template_id=tid,
        content="Updated: Hello {{ name }}, welcome!",
        changelog="Made the greeting more welcoming.",
        created_at=now,
    )
    storage.save_version(version)
    versions = storage.get_versions(tid)
    assert len(versions) == 1
    assert versions[0].version_number == "2.0.0"
