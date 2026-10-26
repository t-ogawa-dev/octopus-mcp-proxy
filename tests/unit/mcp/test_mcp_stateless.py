"""
Tests for MCP 2026-07-28 specification compatibility.

Covers:
- Stateless clients can call tools/list and tools/call without initialize (no Mcp-Session-Id)
- server/discover returns protocolVersions without creating a session
- Stale / forged Mcp-Session-Id is still rejected (old-spec behavior preserved)
- Legacy initialize → session flow continues to work
"""

import json

from app.models.models import Capability, McpService, Service

# ---------------------------------------------------------------------------
# Helpers / shared fixtures
# ---------------------------------------------------------------------------


def _make_public_mcp_with_tool(db):
    """Create a minimal public MCP service with one tool capability."""
    mcp_service = McpService(
        name="Discover Test",
        identifier="discover-test",
        routing_type="subdomain",
        access_control="public",
        is_enabled=True,
    )
    db.session.add(mcp_service)
    db.session.commit()

    service = Service(
        name="Weather App",
        service_type="api",
        mcp_url="https://api.example.com",
        mcp_service_id=mcp_service.id,
        is_enabled=True,
        access_control="public",
    )
    db.session.add(service)
    db.session.commit()

    cap = Capability(
        name="get_weather",
        description="Get current weather",
        capability_type="tool",
        app_id=service.id,
        url="/weather",
        headers="{}",
        body_params='{"properties": {"city": {"type": "string"}}, "required": ["city"]}',
        is_enabled=True,
        access_control="public",
    )
    db.session.add(cap)
    db.session.commit()
    return mcp_service, service, cap


def _post(client, payload, *, subdomain="discover-test", accept_sse=False):
    headers = {"Content-Type": "application/json"}
    if accept_sse:
        headers["Accept"] = "text/event-stream"
    return client.post(
        f"/mcp?subdomain={subdomain}",
        data=json.dumps(payload),
        headers=headers,
    )


# ---------------------------------------------------------------------------
# 1. Stateless client — no initialize, no Mcp-Session-Id
# ---------------------------------------------------------------------------


class TestStatelessClientNoSession:
    def test_tools_list_without_initialize(self, client, db):
        """2026-07-28 client: tools/list succeeds with no prior initialize."""
        _make_public_mcp_with_tool(db)
        resp = _post(client, {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}})
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert "result" in data
        assert "tools" in data["result"]
        tools = data["result"]["tools"]
        assert len(tools) == 1
        # MCP-service-level aggregation prefixes tool names with "<identifier>_<App>:"
        assert tools[0]["name"].endswith("get_weather")

    def test_tools_list_via_sse_without_session(self, client, db):
        """Streamable-HTTP (Accept: text/event-stream) without Mcp-Session-Id must NOT be rejected."""
        _make_public_mcp_with_tool(db)
        resp = _post(
            client,
            {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}},
            accept_sse=True,
        )
        assert resp.status_code == 200

    def test_tools_list_meta_protocol_version(self, client, db):
        """Client may include _meta with protocol version; request must still be handled."""
        _make_public_mcp_with_tool(db)
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/list",
            "params": {
                "_meta": {
                    "io.modelcontextprotocol/protocolVersion": "2026-07-28",
                    "io.modelcontextprotocol/clientCapabilities": {"tools": {}},
                }
            },
        }
        resp = _post(client, payload)
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert "result" in data


# ---------------------------------------------------------------------------
# 2. server/discover — 2026-07-28 stateless discovery
# ---------------------------------------------------------------------------


class TestServerDiscover:
    def test_server_discover_returns_protocol_versions(self, client, db):
        """server/discover must return protocolVersions listing 2026-07-28."""
        _make_public_mcp_with_tool(db)
        resp = _post(client, {"jsonrpc": "2.0", "id": 1, "method": "server/discover", "params": {}})
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert "result" in data
        result = data["result"]
        assert "protocolVersions" in result
        assert "2026-07-28" in result["protocolVersions"]
        assert "2024-11-05" in result["protocolVersions"]

    def test_server_discover_returns_capabilities(self, client, db):
        """server/discover must include server capabilities."""
        _make_public_mcp_with_tool(db)
        resp = _post(client, {"jsonrpc": "2.0", "id": 1, "method": "server/discover", "params": {}})
        data = json.loads(resp.data)
        assert "capabilities" in data["result"]
        assert "tools" in data["result"]["capabilities"]

    def test_server_discover_returns_no_session_id(self, client, db):
        """server/discover must NOT create a session."""
        _make_public_mcp_with_tool(db)
        resp = _post(client, {"jsonrpc": "2.0", "id": 1, "method": "server/discover", "params": {}})
        data = json.loads(resp.data)
        assert "sessionId" not in data.get("result", {})

    def test_server_discover_via_sse_without_session(self, client, db):
        """server/discover over SSE transport without Mcp-Session-Id must not be rejected."""
        _make_public_mcp_with_tool(db)
        resp = _post(
            client,
            {"jsonrpc": "2.0", "id": 1, "method": "server/discover", "params": {}},
            accept_sse=True,
        )
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# 3. Legacy flow (2024-11-05) still works
# ---------------------------------------------------------------------------


class TestLegacyInitializeFlow:
    def test_initialize_returns_session_id(self, client, db):
        """Legacy 2024-11-05 clients: initialize still returns sessionId."""
        _make_public_mcp_with_tool(db)
        resp = _post(
            client,
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
        )
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert "result" in data
        assert "sessionId" in data["result"]

    def test_initialize_protocol_version_backward_compat(self, client, db):
        """Legacy initialize returns 2024-11-05 protocolVersion string."""
        _make_public_mcp_with_tool(db)
        resp = _post(client, {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
        data = json.loads(resp.data)
        assert data["result"]["protocolVersion"] == "2024-11-05"


# ---------------------------------------------------------------------------
# 4. Invalid (stale/forged) session ID is still rejected
# ---------------------------------------------------------------------------


class TestInvalidSessionRejected:
    def test_stale_session_id_rejected(self, client, db):
        """A request with an unrecognised Mcp-Session-Id over SSE must be rejected."""
        _make_public_mcp_with_tool(db)
        resp = client.post(
            "/mcp?subdomain=discover-test",
            data=json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}),
            headers={
                "Content-Type": "application/json",
                "Accept": "text/event-stream",
                "Mcp-Session-Id": "totally-fake-session-id",
            },
        )
        assert resp.status_code == 400
        data = json.loads(resp.data)
        assert data["error"]["code"] == -32600
