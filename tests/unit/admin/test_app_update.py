"""
Tests for partial updates of Apps and custom templates via PUT
"""

import json
from unittest.mock import patch

import pytest

from app.models.models import McpService, McpServiceTemplate, Service


@pytest.fixture
def stdio_app(db):
    mcp_service = McpService(identifier="upd", name="Update MCP", routing_type="path", access_control="public")
    db.session.add(mcp_service)
    db.session.commit()
    app = Service(
        mcp_service_id=mcp_service.id,
        name="StdioApp",
        service_type="mcp",
        mcp_transport="stdio",
        stdio_command="npx",
        stdio_args=json.dumps(["-y", "server"]),
        stdio_env=json.dumps({"API_KEY": "{{KEY}}"}),
        common_headers=json.dumps({"X-Keep": "1"}),
    )
    db.session.add(app)
    db.session.commit()
    return app


@patch("app.services.mcp_discovery.discover_stdio_mcp_capabilities", return_value=0)
def test_put_without_headers_keeps_existing_settings(mock_discover, auth_client, db, stdio_app):
    resp = auth_client.put(f"/api/apps/{stdio_app.id}", json={"description": "updated"})

    assert resp.status_code == 200
    body = resp.get_json()
    assert body["description"] == "updated"
    assert body["common_headers"] == {"X-Keep": "1"}
    assert body["stdio_args"] == ["-y", "server"]
    assert body["stdio_env"] == {"API_KEY": "{{KEY}}"}


@patch("app.services.mcp_discovery.discover_stdio_mcp_capabilities", return_value=0)
def test_put_updates_stdio_settings_and_rediscovers(mock_discover, auth_client, db, stdio_app):
    resp = auth_client.put(
        f"/api/apps/{stdio_app.id}",
        json={"stdio_command": "uvx", "stdio_args": ["mcp-server"], "common_headers": {}},
    )

    body = resp.get_json()
    assert body["stdio_command"] == "uvx"
    assert body["stdio_args"] == ["mcp-server"]
    assert body["common_headers"] == {}
    mock_discover.assert_called_once_with(stdio_app.id, "uvx", ["mcp-server"], {"API_KEY": "{{KEY}}"}, None)


def test_template_put_without_headers_keeps_existing_headers(auth_client, db):
    template = McpServiceTemplate(
        name="Custom",
        template_type="custom",
        service_type="api",
        common_headers=json.dumps({"Authorization": "Bearer {{TOKEN}}"}),
    )
    db.session.add(template)
    db.session.commit()

    resp = auth_client.put(f"/api/mcp-templates/{template.id}", json={"description": "new"})

    assert resp.status_code == 200
    db.session.refresh(template)
    assert json.loads(template.common_headers) == {"Authorization": "Bearer {{TOKEN}}"}
