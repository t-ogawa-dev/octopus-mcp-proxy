# Claude Development Guide

This file defines the working rules for AI agents and developers modifying Octopus MCP Proxy. See [`docs/DEVELOPMENT.md`](docs/DEVELOPMENT.md) for project structure and testing details.

## Project Overview

- Flask application running on Python 3.10 or later
- HTTP and stdio relay for FastMCP/MCP protocols
- Data management with Flask-SQLAlchemy and Alembic
- Admin UI, REST API, and MCP endpoints provided by the same application factory
- Docker Compose services: `caddy`, `web`, `mcp`, `redis`, and `db`

## Before Making Changes

1. Start from the target file, symbol, failing test, or reproduction steps.
2. Read the nearby implementation, callers, and related tests to identify the layer that controls the behavior.
3. Form one falsifiable hypothesis and choose the cheapest check that can disprove it.
4. Check existing uncommitted changes and never overwrite or discard user changes.

## Layers and Ownership

- Route registration and application initialization: `app/__init__.py`
- Configuration: `app/config/config.py`
- Authentication and admin UI: `app/controllers/auth_controller.py`, `admin_controller.py`
- REST API: `app/controllers/api_controller.py`
- MCP protocol: `app/controllers/mcp_controller.py`, `admin_mcp_controller.py`
- Database models: `app/models/models.py`
- Core logic: `app/services/`
- Jinja2 templates: `app/views/templates/`
- CSS, JavaScript, and images: `app/assets/`
- Database migrations: `db/migrations/versions/`
- Tests: `tests/unit/`, `tests/integration/`, `tests/e2e/`

Keep complex business logic out of controllers and place reusable logic in `app/services/`. When changing the database schema, update the model, Alembic migration, and tests together.

## Coding Conventions

- Preserve the existing Flask Blueprint, SQLAlchemy ORM, and application-factory patterns.
- Use `snake_case` for Python files, functions, and variables; use `PascalCase` for classes.
- Treat `pyproject.toml` as the source of truth for Ruff. Do not work around line-length warnings manually.
- Update related tests and documentation when changing a public API, route, or model contract.
- Never put secrets, tokens, or real data in source code, logs, or screenshots.
- Do not edit generated assets manually; regenerate them with existing scripts.
- Do not mix unrelated refactoring, dependency updates, or formatting changes into a task.
- Add comments only where the intent cannot be understood from the code.

## Validation Commands

```bash
# Static checks and formatting validation
./run_check.sh

# Automatic fixes and formatting
./run_format.sh

# Full test suite with coverage
./run_tests.sh

# Focused test
pytest tests/unit/path/to/test_file.py -q

# Regenerate screenshots (requires Playwright Chromium)
python scripts/capture_screenshots.py
```

After making changes, run the test or check closest to the changed code first, then broaden validation as needed. For template, CSS, or image changes, also run the related E2E tests or review the generated screenshots.

## Running the Application

```bash
# Recommended: Docker Compose
cp .env.example .env
docker compose up -d

# Local Flask development server
source .venv/bin/activate
python run.py
```

Use `FLASK_ENV=production` for production-like runs. Set `SECRET_KEY`, admin credentials, the database URL, and `ACCELMCP_ADMIN_API_KEY` through environment variables. Default credentials are for demos and validation only; never use them in production.

## Completion Checklist

- Briefly report the changed files and test results.
- Clearly report skipped validation, existing warnings, and unresolved risks.
- Do not create commits or branches unless explicitly requested.
