[日本語](../TESTING.md) | English

# MCP Server - Testing Guide

## Overview

This project uses `pytest` for testing. The structure is similar to Rails' RSpec, testing the model, API, and view layers.

## Test Structure

```
tests/
├── __init__.py                     # Test package init
├── conftest.py                     # pytest configuration and fixtures
├── conftest_playwright.py          # Playwright configuration
├── README.md                       # Test documentation (Japanese)
├── README.en.md                    # Test documentation (English)
├── unit/                           # Unit / integration tests
│   ├── admin/
│   │   └── test_admin_settings.py  # Admin settings tests
│   ├── infrastructure/
│   │   ├── test_database_schema.py # DB schema tests
│   │   ├── test_error_responses.py # Error response tests
│   │   ├── test_i18n.py            # i18n tests
│   │   └── test_timeout_feature.py # Timeout feature tests
│   ├── logging/
│   │   ├── test_connection_logs.py # Connection log tests
│   │   └── test_log_search.py      # Log search tests
│   ├── mcp/
│   │   ├── test_capability_integration.py  # Capability integration tests
│   │   ├── test_capability_testing.py      # Capability testing features
│   │   ├── test_mcp_protocol.py            # MCP protocol tests
│   │   ├── test_mcp_services.py            # MCP service tests
│   │   ├── test_prompt_and_resource_capability.py # Prompt and resource tests
│   │   └── test_stdio_mcp.py               # stdio MCP tests
│   ├── security/
│   │   ├── test_permissions.py     # Permission tests
│   │   └── test_security.py        # Security tests
│   ├── templates/
│   │   ├── test_prompt_templates.py        # Prompt template tests
│   │   ├── test_template_import_export.py  # Template import/export tests
│   │   └── test_variables.py               # Variable tests
│   └── ui/
│       ├── test_javascript_static.py  # JavaScript static file tests
│       └── test_modal_and_sync.py     # Modal and sync tests
├── e2e/                            # E2E tests (Playwright)
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_login.py               # Login page
│   ├── test_dashboard.py           # Dashboard
│   ├── test_javascript_errors.py   # JavaScript error checks
│   ├── accounts/
│   │   └── test_accounts.py        # Account management
│   ├── capabilities/
│   │   ├── test_capabilities.py
│   │   └── test_capabilities_page.py
│   ├── mcp_services/
│   │   └── test_mcp_services.py    # MCP service management
│   ├── mcp_templates/
│   │   └── test_templates.py       # Template management
│   ├── security/
│   │   └── test_security.py        # Security E2E tests
│   ├── services/
│   │   └── test_services.py        # Service management
│   └── variables/
│       └── test_variables.py       # Variable management
└── reports/                        # Test reports (auto-generated)
```

## Setup

### 1. Install test dependencies

```bash
pip install -r requirements.txt
```

Or install individually:

```bash
pip install pytest pytest-flask pytest-cov pytest-mock pytest-playwright
```

### 2. Install Playwright browsers (for E2E tests)

```bash
./setup_playwright.sh
```

Or:

```bash
python -m playwright install
```

### 3. Running tests in Docker

```bash
docker compose exec web bash
pytest
```

## Running Tests

### Run unit / integration tests

```bash
pytest
```

Or (with coverage, report written to `htmlcov/`):

```bash
./run_tests.sh
```

Running `pytest` without arguments and `run_tests.sh` only run `tests/unit` and `tests/integration`.
E2E tests need a running server and a browser, so run them separately as described below.

### Run tests in a specific file

```bash
pytest tests/unit/mcp/test_mcp_protocol.py
```

### Run tests in a specific class

```bash
pytest tests/unit/mcp/test_mcp_protocol.py::TestMcpProtocol
```

### Run a specific test case

```bash
pytest tests/unit/mcp/test_mcp_protocol.py::TestMcpProtocol::test_tools_list_public_access
```

### Run with verbose output

```bash
pytest -v
```

### Run with coverage

```bash
pytest --cov=app --cov-report=term-missing
```

### Generate HTML coverage report

```bash
pytest --cov=app --cov-report=html
```

Report is generated at `htmlcov/index.html`.

## Test Types

### 1. MCP Protocol Tests (`unit/mcp/`)

Tests for each MCP protocol endpoint, capability registration/execution, and stdio connections.

```python
def test_tools_list_public_access(self, client, db):
    """Can retrieve tools/list for a public service without authentication"""
    response = client.post(
        '/mcp',
        json={'jsonrpc': '2.0', 'id': 1, 'method': 'tools/list'},
        headers={'X-Subdomain': 'myservice'}
    )
    assert response.status_code == 200
```

### 2. Security Tests (`unit/security/`)

Tests for permission management, authentication, and brute-force protection.

### 3. Template Tests (`unit/templates/`)

Tests for built-in template import/export, variable features, and prompt templates.

### 4. Logging Tests (`unit/logging/`)

Tests for MCP connection log recording, search, and CSV export.

### 5. Infrastructure Tests (`unit/infrastructure/`)

Tests for DB schema, error responses, i18n, and timeout features.

### 6. E2E Tests (`e2e/`) - Playwright

End-to-end tests using a real browser (equivalent to Capybara).

**Files:**

- `e2e/test_login.py` - Login/Logout
- `e2e/test_dashboard.py` - Dashboard
- `e2e/test_javascript_errors.py` - JavaScript error detection
- `e2e/services/test_services.py` - App management (create, edit, connection test)
- `e2e/capabilities/test_capabilities.py` - Capabilities management
- `e2e/capabilities/test_capability_schema_roundtrip.py` - Schema stays identical between the new and edit pages
- `e2e/accounts/test_accounts.py` - Account management
- `e2e/mcp_services/test_mcp_services.py` - MCP service management
- `e2e/mcp_templates/test_templates.py` - Template management
- `e2e/security/test_security.py` - Security E2E tests
- `e2e/variables/test_variables.py` - Variable management

```python
def test_login_with_valid_credentials(self, page: Page):
    """Can log in with valid credentials"""
    page.goto("http://localhost:5000/login")

    page.fill('input[name="username"]', "accel")
    page.fill('input[name="password"]', "universe")
    page.click('button[type="submit"]')

    page.wait_for_url("http://localhost:5000/")
    expect(page).to_have_url("http://localhost:5000/")
```

**Running E2E tests:**

```bash
# Recommended: run in Docker (image includes the browser)
docker compose up -d
docker compose --profile e2e run --rm e2e

# Running locally (server started and Playwright browsers installed)
pytest tests/e2e/

# Run tests for a specific page
pytest tests/e2e/test_login.py
pytest tests/e2e/services/test_services.py
pytest tests/e2e/mcp_templates/test_templates.py

# Run by marker (a path is required)
pytest tests/e2e/ -m e2e

# Disable headless mode (show browser)
pytest tests/e2e/ --headed

# Run with specific browser
pytest tests/e2e/ --browser chromium
pytest tests/e2e/ --browser firefox
pytest tests/e2e/ --browser webkit
```

## Fixtures

Main fixtures available in tests:

**For unit/API tests:**

- `app` - Flask application
- `db` - Test database
- `client` - Test client (unauthenticated)
- `auth_client` - Authenticated test client
- `sample_service` - Sample service
- `sample_capability` - Sample capability
- `sample_account` - Sample connection account
- `sample_template` - Sample template

**For E2E tests (Playwright):**

- `page` - Playwright page object
- `browser` - Browser instance
- `context` - Browser context

Usage example:

```python
def test_something(self, auth_client, sample_service):
    """Test using fixtures"""
    response = auth_client.get(f'/services/{sample_service.id}')
    assert response.status_code == 200
```

```python
def test_e2e_example(self, page: Page):
    """E2E test example"""
    page.goto("http://localhost:5000/login")
    page.fill('input[name="username"]', "accel")
    page.click('button[type="submit"]')
```

## Test Database

Tests use an SQLite in-memory database. It is automatically cleaned up after each test run.

```python
class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
```

## CI/CD Integration

Example of running tests in a CI environment such as GitHub Actions:

```yaml
- name: Install dependencies
  run: |
    pip install -r requirements.txt
    python -m playwright install

- name: Run unit tests
  run: |
    pytest tests/unit/ --cov=app --cov-report=xml

- name: Run E2E tests
  run: |
    docker compose up -d
    pytest tests/e2e/
    docker compose down

- name: Upload coverage
```
