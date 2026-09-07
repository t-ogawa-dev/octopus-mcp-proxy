# Development Guide

## System responsibilities

Octopus MCP Proxy exposes the admin UI, REST API, and MCP endpoints from one Flask application factory. MCP requests are relayed using service, capability, connection-account, and permission data, then recorded in connection and audit logs.

## Directory responsibilities

| Path                      | Responsibility                                                       |
| ------------------------- | -------------------------------------------------------------------- |
| `app/__init__.py`         | Application factory, extensions, blueprint registration, `/health`   |
| `app/config/`             | Configuration classes and environment variables                      |
| `app/controllers/`        | HTTP routes, authentication, REST API, MCP entry points              |
| `app/models/`             | SQLAlchemy models and database extension                             |
| `app/services/`           | MCP relay, permissions, logging, template sync, variable replacement |
| `app/views/templates/`    | Jinja2 HTML templates                                                |
| `app/assets/`             | CSS, JavaScript, and images                                          |
| `db/migrations/`          | Alembic migrations                                                   |
| `db/seeds/`               | Initial admin, settings, and built-in template data                  |
| `data/builtin_templates/` | Built-in MCP template YAML definitions                               |
| `tests/unit/`             | Focused unit tests                                                   |
| `tests/integration/`      | Cross-component tests                                                |
| `tests/e2e/`              | Playwright browser tests                                             |
| `scripts/`                | Development helpers, including screenshot capture                    |

See [Directory Structure](STRUCTURE.en.md) for the broader file map.

## Typical change workflow

### Adding an admin page or API

1. Add the route to the appropriate Blueprint controller.
2. Put business logic and external calls in `app/services/`.
3. Update the model and an Alembic migration if the database changes.
4. Update templates, JavaScript, and i18n dictionaries as needed.
5. Check authentication, permissions, error responses, and audit logging.
6. Add unit/integration tests and update E2E coverage for UI changes.

### Changing MCP capabilities or relay behavior

Keep `app/controllers/mcp_controller.py` focused on protocol entry points and routing. Prefer the existing service layer for relay, capability resolution, variable replacement, and permission checks. Preserve behavior for `tools/list`, `tools/call`, prompts, resources, stdio, Streamable HTTP, and legacy clients. Verify JSON-RPC errors, HTTP status codes, and connection logs.

### Changing the database schema

```bash
flask db migrate -m "describe schema change"
flask db upgrade
```

Read generated migrations before applying them. Check existing data, NULL/default behavior, and rollback implications. Also review `db/migrate.py` and the existing migration workflow.

## Configuration and runtime

The main settings are in `app/config/config.py`:

- `DATABASE_URL`: database URL; SQLite is the default
- `SECRET_KEY`: Flask session signing key
- `ADMIN_USERNAME`, `ADMIN_PASSWORD`: initial admin credentials
- `ACCELMCP_ADMIN_API_KEY`: Admin MCP bearer key
- `REDIS_URL`: shared Streamable HTTP session store; process memory is used when unset
- `LOG_LEVEL`: logging level
- `FLASK_DEBUG` / `FLASK_ENV`: development or production mode

In Docker Compose, `web` runs migrations and `mcp` serves the MCP endpoint. Redis shares Streamable HTTP sessions across replicas.

## Quality checks

```bash
./run_check.sh
pytest tests/unit/path/to/test_file.py -q
pytest tests/integration/ -q
pytest tests/e2e/ -v
./run_tests.sh
```

Ruff, Ruff format, and mypy are configured in `pyproject.toml`. Playwright browsers are required for E2E tests and screenshot capture:

```bash
./setup_playwright.sh
python -m playwright install chromium
python scripts/capture_screenshots.py
```

Screenshots are written to `docs/assets/screenshots/`.

## Change principles

- Preserve the existing ownership boundaries and naming conventions.
- Check authentication, authorization, input validation, and logging for new features.
- Never put secrets in test data, logs, screenshots, or documentation.
- Do not discard unrelated uncommitted changes.
- Avoid unrelated refactoring and dependency updates.
- Update tests and relevant documentation when behavior changes.
