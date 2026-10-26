"""
E2E tests for the App (Service) pages under an MCP service:
/mcp-services/<id>/apps, /apps/new and /apps/<id>/edit
"""

import uuid

import pytest
from playwright.sync_api import Page, expect

from tests.e2e.helpers import e2e_url

SUBMIT = 'button[type="submit"][form="service-form"], #service-form button[type="submit"]'


@pytest.fixture
def mcp_service_id(authenticated_page: Page):
    page = authenticated_page
    suffix = uuid.uuid4().hex[:8]
    service = page.request.post(
        e2e_url("/api/mcp-services"), data={"name": f"E2E Apps {suffix}", "identifier": f"e2e-apps-{suffix}"}
    ).json()
    yield service["id"]
    page.request.delete(e2e_url(f"/api/mcp-services/{service['id']}"))


def _apps(page: Page, mcp_service_id):
    return page.request.get(e2e_url(f"/api/mcp-services/{mcp_service_id}/apps")).json()


def test_apps_list_page_loads(authenticated_page: Page, mcp_service_id):
    page = authenticated_page
    page.goto(e2e_url(f"/mcp-services/{mcp_service_id}/apps"))
    page.wait_for_load_state("networkidle")

    expect(page).to_have_url(e2e_url(f"/mcp-services/{mcp_service_id}/apps"))


def test_create_api_app_with_header(authenticated_page: Page, mcp_service_id):
    page = authenticated_page
    name = f"E2EApi{uuid.uuid4().hex[:6]}"
    page.goto(e2e_url(f"/mcp-services/{mcp_service_id}/apps/new"))
    page.wait_for_load_state("networkidle")

    page.fill("#name", name)
    page.fill("#description", "created by e2e")
    header_rows = page.locator("#headers-container .key-value-row")
    if header_rows.count() == 0:
        page.click('[data-action="add-header"]')
    header_rows.last.locator("input").nth(0).fill("X-E2E")
    header_rows.last.locator("input").nth(1).fill("yes")
    page.click(SUBMIT)
    page.wait_for_url(e2e_url(f"/mcp-services/{mcp_service_id}/apps"))

    app = next(a for a in _apps(page, mcp_service_id) if a["name"] == name)
    assert app["service_type"] == "api"
    assert app["common_headers"] == {"X-E2E": "yes"}


def test_editing_app_description_keeps_headers(authenticated_page: Page, mcp_service_id):
    page = authenticated_page
    app = page.request.post(
        e2e_url(f"/api/mcp-services/{mcp_service_id}/apps"),
        data={"name": f"E2EEdit{uuid.uuid4().hex[:6]}", "service_type": "api", "common_headers": {"X-Keep": "1"}},
    ).json()

    page.goto(e2e_url(f"/mcp-services/{mcp_service_id}/apps/{app['id']}/edit"))
    page.wait_for_load_state("networkidle")
    page.fill("#description", "edited by e2e")
    page.click(SUBMIT)
    page.wait_for_url(e2e_url(f"/mcp-services/{mcp_service_id}/apps/{app['id']}"))

    updated = page.request.get(e2e_url(f"/api/apps/{app['id']}")).json()
    assert updated["description"] == "edited by e2e"
    assert updated["common_headers"] == {"X-Keep": "1"}


def test_http_connection_test_reports_unreachable_server(authenticated_page: Page, mcp_service_id):
    page = authenticated_page
    page.goto(e2e_url(f"/mcp-services/{mcp_service_id}/apps/new"))
    page.wait_for_load_state("networkidle")

    page.check('input[name="service_type"][value="mcp"]')
    page.fill("#mcp_url", "http://127.0.0.1:9/mcp")
    page.click("#test-connection-btn")

    expect(page.locator("#connection-test-result")).to_contain_text("✗", timeout=20000)


def test_stdio_connection_test_reports_undefined_variable(authenticated_page: Page, mcp_service_id):
    page = authenticated_page
    page.goto(e2e_url(f"/mcp-services/{mcp_service_id}/apps/new"))
    page.wait_for_load_state("networkidle")

    page.check('input[name="service_type"][value="mcp"]')
    page.check('input[name="mcp_transport"][value="stdio"]')
    page.fill("#stdio_command", "npx")
    page.fill("#stdio_args", "{{UNDEFINED_E2E_VAR}}")
    page.click("#test-stdio-btn")

    expect(page.locator("#stdio-test-result")).to_contain_text("UNDEFINED_E2E_VAR")
