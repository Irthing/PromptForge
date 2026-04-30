<div align="center">

# PromptForge

**Professional Prompt Engineering Toolkit**

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Template management, A/B testing, evaluation and optimization for LLM prompts.

[Features](#features) · [Quick Start](#quick-start) · [API Docs](#api-documentation) · [Architecture](#architecture)

</div>

---

## Overview

PromptForge is a unified platform designed for AI developers and prompt engineers who need to **manage, test, evaluate, and optimize** their LLM prompts at scale. Whether you're building AI-powered applications or fine-tuning prompt strategies, PromptForge provides the tools you need.

## Features

- **Template Management** — Create, organize, version-control, and search prompt templates with categories and tags
- **Jinja2 Rendering** — Dynamic prompt templates with variable substitution using familiar Jinja2 syntax (`{{ variable }}`)
- **Prompt Evaluation** — Score prompts against configurable criteria (clarity, specificity, structure)
- **Variant Generation** — Automatically generate alternative versions of your prompts for A/B testing
- **Full-Text Search** — SQLite FTS5 powered search across all your templates
- **Version History** — Track every change to your prompts with full changelog
- **REST API** — Clean FastAPI endpoints with automatic OpenAPI documentation
- **Web Dashboard** — Modern dark-themed UI for visual management
- **Analytics** — Track template usage and test results

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/Irthing/PromptForge.git
cd PromptForge

# Install dependencies
pip install -e ".[dev]"

# Run the server
python main.py
```

The dashboard will be available at `http://localhost:8000`, and the API docs at `http://localhost:8000/docs`.

### Create Your First Template

```python
from src.core.storage import Storage
from src.core.models import PromptTemplate
from datetime import datetime

storage = Storage()

template = PromptTemplate(
    id=0,
    name="Code Review Assistant",
    content="You are a senior {{ language }} developer. Review the following code for bugs, performance issues, and best practices:\n\n```{{ language }}\n{{ code }}\n```\n\nProvide specific, actionable feedback.",
    category="code-review",
    tags=["code", "review", "developer"],
    variables=["language", "code"],
    version="1.0.0",
    created_at=datetime.now(),
    updated_at=datetime.now(),
    metadata={"model": "gpt-4", "temperature": 0.3}
)

storage.save_template(template)
```

### Render a Template

```python
from src.core.engine import PromptEngine

rendered = PromptEngine.render_template(
    template,
    {"language": "python", "code": "def add(a, b): return a + b"}
)
print(rendered)
```

## API Documentation

PromptForge provides a full REST API with automatic OpenAPI/Swagger documentation.

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/templates` | Create a new template |
| `GET` | `/api/templates` | List all templates |
| `GET` | `/api/templates/{id}` | Get template details |
| `PUT` | `/api/templates/{id}` | Update a template |
| `DELETE` | `/api/templates/{id}` | Delete a template |
| `POST` | `/api/templates/{id}/render` | Render template with variables |
| `POST` | `/api/templates/{id}/evaluate` | Evaluate prompt quality |
| `POST` | `/api/templates/{id}/optimize` | Get optimization suggestions |
| `POST` | `/api/templates/{id}/variants` | Generate prompt variants |
| `GET` | `/api/analytics` | Get usage analytics |

Visit `/docs` for the interactive Swagger UI.

## Architecture

```
promptforge/
├── main.py                    # Application entry point
├── pyproject.toml             # Project configuration
├── LICENSE                    # MIT License
├── src/
│   ├── __init__.py
│   ├── core/
│   │   ├── models.py          # Data models (dataclasses)
│   │   ├── engine.py          # Prompt rendering, evaluation, optimization
│   │   └── storage.py         # SQLite storage layer with FTS5
│   └── api/
│       ├── server.py          # FastAPI endpoints
│       └── schemas.py         # Pydantic request/response models
├── web/
│   ├── static/
│   │   ├── css/style.css      # Dashboard styles (dark theme)
│   │   └── js/app.js          # Dashboard JavaScript
│   └── templates/
│       └── index.html         # Main dashboard page
└── tests/
    ├── test_engine.py         # Engine unit tests
    └── test_storage.py        # Storage unit tests
```

## Running Tests

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_engine.py
```

## Tech Stack

- **Backend**: Python 3.10+, FastAPI, Uvicorn
- **Database**: SQLite with FTS5 full-text search
- **Templating**: Jinja2
- **Validation**: Pydantic v2
- **Testing**: pytest, pytest-asyncio
- **Frontend**: Vanilla JavaScript, Custom CSS (dark theme)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
