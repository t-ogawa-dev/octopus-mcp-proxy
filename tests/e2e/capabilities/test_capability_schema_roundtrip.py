"""
E2E tests for the capability new/edit forms.

The new and edit pages build the JSON Schema (body_params) with separate code, so
a capability created on the new page and re-saved unchanged on the edit page must
keep exactly the same schema.
"""

import uuid

import pytest
from playwright.sync_api import Page, expect

from tests.e2e.helpers import e2e_url


@pytest.fixture
def api_app(authenticated_page: Page):
    """An MCP service with one API app, created through the REST API and removed afterwards."""
    page = authenticated_page
    suffix = uuid.uuid4().hex[:8]
    mcp_service = page.request.post(
        e2e_url("/api/mcp-services"), data={"name": f"E2E Schema {suffix}", "identifier": f"e2e-schema-{suffix}"}
    ).json()
    app = page.request.post(
        e2e_url(f"/api/mcp-services/{mcp_service['id']}/apps"),
        data={"name": f"SchemaApp{suffix}", "service_type": "api", "mcp_url": "https://api.example.com"},
    ).json()
    yield mcp_service["id"], app["id"]
    page.request.delete(e2e_url(f"/api/mcp-services/{mcp_service['id']}"))


def _fill_tree_node(node, name, type_=None, description=None, default=None, required=False):
    node.locator(".tree-param-name").first.fill(name)
    if type_:
        node.locator(".tree-param-type").first.select_option(type_)
    if description is not None:
        node.locator(".tree-param-description").first.fill(description)
    if default is not None:
        node.locator(".tree-param-default").first.fill(default)
    if required:
        node.locator(".tree-param-required").first.check()


def _create_capability(page: Page, mcp_service_id, app_id, fill_params):
    page.goto(e2e_url(f"/mcp-services/{mcp_service_id}/apps/{app_id}/capabilities/new"))
    page.wait_for_load_state("networkidle")
    name = f"cap_{uuid.uuid4().hex[:6]}"
    page.fill("#name", name)
    page.fill("#url", "https://api.example.com/weather")
    page.fill("#description", "Weather lookup")
    page.fill("#timeout_seconds", "120")
    fill_params(page)

    with page.expect_response(lambda r: r.url.endswith(f"/api/apps/{app_id}/capabilities")) as created:
        page.click('button[type="submit"][form="capability-form"]')
    # The page navigates away right after saving, so look the capability up instead of reading the response
    assert created.value.status == 201
    capabilities = page.request.get(e2e_url(f"/api/apps/{app_id}/capabilities")).json()
    return next(cap["id"] for cap in capabilities if cap["name"] == name)


def _resave_on_edit_page(page: Page, capability_id):
    page.goto(e2e_url(f"/capabilities/{capability_id}/edit"))
    page.wait_for_load_state("networkidle")
    with page.expect_response(
        lambda r: r.url.endswith(f"/api/capabilities/{capability_id}") and r.request.method == "PUT"
    ) as saved:
        page.click('button[type="submit"][form="capability-form"]')
    assert saved.value.ok


def _fetch(page: Page, capability_id):
    return page.request.get(e2e_url(f"/api/capabilities/{capability_id}")).json()


def _normalized(schema):
    """The order of "required" carries no meaning, so compare it as a set."""
    return {**schema, "required": sorted(schema.get("required", []))}


def _fill_post_params(page: Page):
    page.select_option("#method", "POST")

    page.click('[data-action="add-llm-param-tree"]')
    _fill_tree_node(
        page.locator("#llm-params-tree-container > .tree-node").nth(0), "city", description="City name", required=True
    )
    page.click('[data-action="add-llm-param-tree"]')
    _fill_tree_node(page.locator("#llm-params-tree-container > .tree-node").nth(1), "days", "integer", "Days", "3")

    page.click('[data-action="add-llm-param-tree"]')
    _fill_tree_node(
        page.locator("#llm-params-tree-container > .tree-node").nth(2), "lang", description="Lang", default="ja"
    )

    page.click('[data-action="add-llm-param-tree"]')
    filters = page.locator("#llm-params-tree-container > .tree-node").nth(3)
    _fill_tree_node(filters, "filters", "object", "Filters")
    filters.locator('[data-action="add-tree-child"]').first.click()
    _fill_tree_node(filters.locator(".tree-children .tree-node").first, "lang", description="Language")

    page.click('[data-action="add-llm-param-tree"]')
    _fill_tree_node(
        page.locator("#llm-params-tree-container > .tree-node").nth(4), "zip", description="Zip", default="123"
    )

    fixed = page.locator("#fixed-params-post-container > .tree-node")
    page.click('[data-action="add-fixed-param-post"]')
    _fill_tree_node(fixed.nth(0), "units", default="metric")
    page.click('[data-action="add-fixed-param-post"]')
    _fill_tree_node(fixed.nth(1), "limit", "integer", default="10")
    page.click('[data-action="add-fixed-param-post"]')
    _fill_tree_node(fixed.nth(2), "tags", "array")
    fixed.nth(2).locator(".tree-array-value").fill("a, b")


def _fill_get_params(page: Page):
    page.select_option("#method", "GET")

    page.click('[data-action="add-llm-param"]')
    row = page.locator("#llm-params-container > *").nth(0)
    row.locator(".llm-param-name").fill("q")
    row.locator(".llm-param-description").fill("Query")
    row.locator(".llm-param-required").check()

    page.click('[data-action="add-fixed-param"]')
    fixed = page.locator("#fixed-params-container .key-value-row").nth(0)
    fixed.locator("input").nth(0).fill("format")
    fixed.locator("input").nth(1).fill("json")


def test_post_tool_schema_survives_edit_without_changes(authenticated_page: Page, api_app):
    page = authenticated_page
    capability_id = _create_capability(page, *api_app, _fill_post_params)

    created = _fetch(page, capability_id)
    schema = created["body_params"]
    assert schema["properties"]["city"]["type"] == "string"
    assert "city" in schema["required"]
    assert schema["properties"]["days"]["type"] == "integer"
    assert schema["properties"]["lang"]["default"] == "ja"
    assert schema["properties"]["filters"]["properties"]["lang"]["type"] == "string"
    assert schema["properties"]["zip"]["default"] == "123"  # a string param keeps a numeric-looking default as text
    assert schema["properties"]["units"]["const"] == "metric"
    assert schema["properties"]["limit"]["const"] == 10
    assert schema["properties"]["tags"]["const"] == ["a", "b"]
    assert created["timeout_seconds"] == 120

    _resave_on_edit_page(page, capability_id)

    resaved = _fetch(page, capability_id)
    assert _normalized(resaved["body_params"]) == _normalized(schema)
    assert resaved["timeout_seconds"] == 120


def test_get_tool_schema_survives_edit_without_changes(authenticated_page: Page, api_app):
    page = authenticated_page
    capability_id = _create_capability(page, *api_app, _fill_get_params)

    created = _fetch(page, capability_id)
    schema = created["body_params"]
    assert schema["properties"]["q"]["type"] == "string"
    assert "q" in schema["required"]
    assert schema["properties"]["format"]["const"] == "json"

    _resave_on_edit_page(page, capability_id)

    assert _normalized(_fetch(page, capability_id)["body_params"]) == _normalized(schema)


def test_timeout_can_be_changed_on_edit_page(authenticated_page: Page, api_app):
    page = authenticated_page
    capability_id = _create_capability(page, *api_app, lambda p: None)

    page.goto(e2e_url(f"/capabilities/{capability_id}/edit"))
    page.wait_for_load_state("networkidle")
    expect(page.locator("#timeout_seconds")).to_have_value("120")
    page.fill("#timeout_seconds", "150")
    with page.expect_response(lambda r: r.url.endswith(f"/api/capabilities/{capability_id}")):
        page.click('button[type="submit"][form="capability-form"]')

    assert _fetch(page, capability_id)["timeout_seconds"] == 150


def test_capability_names_with_markup_are_rendered_as_text(authenticated_page: Page, api_app):
    """Names and descriptions from upstream MCP servers must never be interpreted as HTML."""
    page = authenticated_page
    mcp_service_id, app_id = api_app
    payload = '<img src=x onerror="window.__xss=1">'
    created = page.request.post(
        e2e_url(f"/api/apps/{app_id}/capabilities"),
        data={
            "name": "xss_probe",
            "capability_type": "tool",
            "url": "https://api.example.com/x",
            "description": payload,
            "body_params": {"properties": {'k"><img src=x onerror="window.__xss=1">': {"type": "string"}}},
        },
    ).json()

    for path in (
        f"/mcp-services/{mcp_service_id}/apps/{app_id}/capabilities",
        f"/capabilities/{created['id']}",
        f"/capabilities/{created['id']}/edit",
    ):
        page.goto(e2e_url(path))
        page.wait_for_load_state("networkidle")
        assert page.evaluate("window.__xss") is None, path
