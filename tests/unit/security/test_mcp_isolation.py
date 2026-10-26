"""
Regression tests for MCP tenant isolation, permission filtering and secret handling
"""

import asyncio
from unittest.mock import patch

import pytest

from app.models.models import (
    AccountPermission,
    AdminCredentials,
    Capability,
    ConnectionAccount,
    McpService,
    Service,
)
from app.services.mcp_handler import MCPHandler


def _rpc(client, identifier, method, params=None, token=None):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    body = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params or {}}
    return client.post(f"/{identifier}/mcp", json=body, headers=headers)


@pytest.fixture
def two_tenants(db):
    """Public MCP service A and restricted MCP service B, each with one app."""
    public_service = McpService(identifier="tenant-a", name="Tenant A", routing_type="path", access_control="public")
    restricted_service = McpService(
        identifier="tenant-b", name="Tenant B", routing_type="path", access_control="restricted"
    )
    db.session.add_all([public_service, restricted_service])
    db.session.commit()

    app_a = Service(mcp_service_id=public_service.id, name="AppA", service_type="api", common_headers="{}")
    app_b = Service(mcp_service_id=restricted_service.id, name="AppB", service_type="api", common_headers="{}")
    db.session.add_all([app_a, app_b])
    db.session.commit()

    db.session.add_all(
        [
            Capability(
                app_id=app_a.id,
                name="visible_tool",
                capability_type="tool",
                url="https://api.example.com/visible",
                headers='{"X-Api-Key": "PUBLIC-KEY"}',
            ),
            Capability(
                app_id=app_a.id,
                name="hidden_tool",
                capability_type="tool",
                url="https://api.example.com/hidden",
                headers='{"X-Api-Key": "SECRET-KEY-123"}',
                access_control="restricted",
            ),
            Capability(
                app_id=app_a.id,
                name="disabled_tool",
                capability_type="tool",
                url="https://api.example.com/disabled",
                is_enabled=False,
            ),
            Capability(
                app_id=app_b.id,
                name="secret_doc",
                capability_type="resource",
                resource_uri="resource://tenant-b/secret",
                template_content="SECRET-B",
            ),
            Capability(
                app_id=app_b.id,
                name="secret_prompt",
                capability_type="prompt",
                template_content="SECRET-PROMPT-B",
            ),
        ]
    )
    db.session.commit()
    return public_service, restricted_service, app_a, app_b


class TestGetCapabilitiesEndpoint:
    def test_get_returns_only_accessible_tools_without_raw_settings(self, client, two_tenants):
        resp = client.get("/tenant-a/mcp")

        assert resp.status_code == 200
        body = resp.get_json()
        names = [tool["name"] for tool in body["capabilities"]["tools"]]
        assert names == ["tenant-a_AppA:visible_tool"]
        raw = resp.get_data(as_text=True)
        assert "SECRET-KEY-123" not in raw
        assert "PUBLIC-KEY" not in raw
        assert "https://api.example.com" not in raw


class TestCrossTenantAccess:
    def test_resources_read_cannot_reach_other_mcp_service(self, client, two_tenants):
        resp = _rpc(client, "tenant-a", "resources/read", {"uri": "resource://tenant-b/secret"})

        body = resp.get_json()
        assert body["error"]["code"] == -32602
        assert "SECRET-B" not in resp.get_data(as_text=True)

    def test_prompts_list_excludes_other_mcp_service(self, client, two_tenants):
        resp = _rpc(client, "tenant-a", "prompts/list")

        assert resp.get_json()["result"]["prompts"] == []

    def test_prompts_get_cannot_reach_other_mcp_service(self, client, two_tenants):
        resp = _rpc(client, "tenant-a", "prompts/get", {"name": "secret_prompt"})

        assert resp.get_json()["error"]["code"] == -32602
        assert "SECRET-PROMPT-B" not in resp.get_data(as_text=True)

    def test_permitted_account_can_read_restricted_tenant_resource(self, client, db, two_tenants):
        _, restricted_service, _, _ = two_tenants
        account = ConnectionAccount(name="B user", bearer_token="tenant-b-token")
        db.session.add(account)
        db.session.commit()
        db.session.add(AccountPermission(account_id=account.id, mcp_service_id=restricted_service.id))
        db.session.commit()

        resp = _rpc(client, "tenant-b", "resources/read", {"uri": "resource://tenant-b/secret"}, token="tenant-b-token")

        assert resp.status_code == 200
        assert resp.get_json()["result"]["contents"][0]["text"] == "SECRET-B"

    def test_account_without_permission_cannot_read_restricted_tenant_resource(self, client, db, two_tenants):
        db.session.add(ConnectionAccount(name="Other", bearer_token="other-token"))
        db.session.commit()

        resp = _rpc(client, "tenant-b", "resources/read", {"uri": "resource://tenant-b/secret"}, token="other-token")

        assert resp.get_json()["error"]["code"] == -32602


class TestLegacyEndpointsRemoved:
    @pytest.mark.parametrize("path", ["/tools/anything", "/mcp/anything"])
    def test_legacy_endpoints_are_gone(self, client, path):
        resp = client.post(path, json={}, headers={"Authorization": "Bearer x"})

        assert resp.status_code in (404, 405)


class TestStdioEnvironment:
    def test_proxy_environment_is_not_passed_to_stdio_server(self, app, monkeypatch):
        monkeypatch.setenv("ACCELMCP_TEST_SECRET", "must-not-leak")
        captured = {}

        def fake_stdio_client(server_params):
            captured["env"] = server_params.env
            raise RuntimeError("stop before spawning")

        with patch("app.services.mcp_handler.stdio_client", fake_stdio_client):
            handler = MCPHandler(None)
            asyncio.run(handler._async_stdio_mcp_call("echo", [], {"MY_VAR": "1"}, None, "tool", {}))

        assert captured["env"]["MY_VAR"] == "1"
        assert "ACCELMCP_TEST_SECRET" not in captured["env"]


class TestForcedCredentialChange:
    @pytest.fixture
    def pending_admin_client(self, client, db):
        cred = AdminCredentials(username="bootstrap_admin", is_initialized=False)
        cred.set_password("bootstrap-pass-1")
        db.session.add(cred)
        db.session.commit()
        with client.session_transaction() as sess:
            sess["admin_logged_in"] = True
            sess["admin_username"] = "bootstrap_admin"
        return client

    def test_general_api_is_blocked_until_credentials_change(self, pending_admin_client):
        resp = pending_admin_client.get("/api/mcp-services")

        assert resp.status_code == 403
        assert resp.get_json()["error"] == "Credential change required"

    def test_language_api_is_allowed_before_credentials_change(self, pending_admin_client):
        resp = pending_admin_client.get("/api/settings/language")

        assert resp.status_code == 200


class TestProductionConfig:
    def test_production_refuses_known_secret_key(self, monkeypatch):
        from app import create_app
        from app.config.config import Config

        class ProdConfig(Config):
            SECRET_KEY = "dev-secret-key-change-in-production"
            SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"

        monkeypatch.setenv("FLASK_ENV", "production")

        with pytest.raises(RuntimeError, match="SECRET_KEY"):
            create_app(ProdConfig)
