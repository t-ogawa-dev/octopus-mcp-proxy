"""
Tests for AccelMCP hub/relay features and Streamable HTTP transport.

Covers the three end-to-end topologies AccelMCP is designed to provide:

  1. MCP client -> AccelMCP -> API server          (API relay)
  2. MCP client -> AccelMCP -> MCP server (HTTP)    (MCP relay)
  3. MCP client -> AccelMCP -> AccelMCP -> MCP ...  (daisy-chain / 連結)

plus Streamable HTTP (SSE) transport on the main /mcp endpoint.

External HTTP calls (httpx) are mocked so these tests are hermetic and do not
depend on any real upstream server.
"""

import json
import logging
from unittest.mock import MagicMock, patch

import pytest

from app.models.models import Capability, McpService, Service


def _make_json_response(payload, status_code=200, headers=None, content_type="application/json"):
    """Build a MagicMock that behaves like an httpx.Response (plain JSON)."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.headers = headers or {}
    # httpx.Response.headers.get(...) is used in code; dict supports .get
    resp.json.return_value = payload
    resp.text = json.dumps(payload)
    resp.raise_for_status.return_value = None
    return resp


def _make_sse_response(payload, status_code=200, headers=None):
    """Build a MagicMock that behaves like an httpx.Response carrying an SSE body."""
    resp = MagicMock()
    resp.status_code = status_code
    merged = {"content-type": "text/event-stream"}
    merged.update(headers or {})
    resp.headers = merged
    resp.text = "data: " + json.dumps(payload) + "\n\n"
    # .json() must NOT be relied upon for SSE; make it raise to catch regressions
    resp.json.side_effect = ValueError("SSE body is not valid JSON for .json()")
    resp.raise_for_status.return_value = None
    return resp


@pytest.fixture
def api_relay_setup(db):
    """Public MCP service -> API app -> tool capability (API relay topology)."""
    mcp_service = McpService(
        name="API Relay MCP",
        identifier="api-relay",
        routing_type="subdomain",
        access_control="public",
        is_enabled=True,
    )
    db.session.add(mcp_service)
    db.session.commit()

    app = Service(
        name="WeatherApp",
        service_type="api",
        mcp_url="https://api.example.com",
        common_headers='{"X-Common": "common-value"}',
        mcp_service_id=mcp_service.id,
        is_enabled=True,
        access_control="public",
    )
    db.session.add(app)
    db.session.commit()

    cap = Capability(
        name="get_weather",
        description="Get weather",
        capability_type="tool",
        app_id=app.id,
        url="https://api.example.com/weather",
        headers='{"X-Cap": "cap-value"}',
        body_params='{"properties": {"city": {"type": "string"}}, "required": ["city"]}',
        is_enabled=True,
        access_control="public",
    )
    db.session.add(cap)
    db.session.commit()
    return {"mcp_service": mcp_service, "app": app, "cap": cap}


@pytest.fixture
def mcp_relay_setup(db):
    """Public MCP service -> MCP app (HTTP transport) -> mcp_tool capability (MCP relay topology)."""
    mcp_service = McpService(
        name="MCP Relay MCP",
        identifier="mcp-relay",
        routing_type="subdomain",
        access_control="public",
        is_enabled=True,
    )
    db.session.add(mcp_service)
    db.session.commit()

    app = Service(
        name="UpstreamMcp",
        service_type="mcp",
        mcp_transport="http",
        mcp_url="https://upstream.example.com/mcp",
        common_headers='{"Authorization": "Bearer upstream-token"}',
        mcp_service_id=mcp_service.id,
        is_enabled=True,
        access_control="public",
    )
    db.session.add(app)
    db.session.commit()

    cap = Capability(
        name="remote_search",
        description="Search on the upstream MCP server",
        capability_type="mcp_tool",
        app_id=app.id,
        headers="{}",
        body_params='{"properties": {"query": {"type": "string"}}, "required": ["query"]}',
        is_enabled=True,
        access_control="public",
    )
    db.session.add(cap)
    db.session.commit()
    return {"mcp_service": mcp_service, "app": app, "cap": cap}


def _tools_call(client, subdomain, tool_name, arguments, headers=None):
    base_headers = {"Content-Type": "application/json"}
    if headers:
        base_headers.update(headers)
    return client.post(
        f"/mcp?subdomain={subdomain}",
        data=json.dumps(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {"name": tool_name, "arguments": arguments},
            }
        ),
        headers=base_headers,
    )


# ---------------------------------------------------------------------------
# 1. API relay: MCP client -> AccelMCP -> API server
# ---------------------------------------------------------------------------


class TestApiRelay:
    @patch("app.services.mcp_handler.httpx.post")
    def test_api_relay_tool_call_success(self, mock_post, client, db, api_relay_setup):
        """tools/call on an API-type capability proxies to the upstream API and returns its data."""
        mock_post.return_value = _make_json_response(
            {"temperature": 22, "condition": "sunny"},
            headers={"content-type": "application/json"},
        )

        resp = _tools_call(client, "api-relay", "api-relay_WeatherApp:get_weather", {"city": "Tokyo"})
        assert resp.status_code == 200
        data = json.loads(resp.data)

        assert "result" in data
        # Inner relay result is JSON-encoded inside the MCP content text
        text = data["result"]["content"][0]["text"]
        inner = json.loads(text)
        assert inner["success"] is True
        assert inner["data"]["condition"] == "sunny"

        # Upstream API was actually called once
        assert mock_post.call_count == 1
        called_url = mock_post.call_args.args[0] if mock_post.call_args.args else mock_post.call_args.kwargs.get("url")
        assert called_url == "https://api.example.com/weather"

    @patch("app.services.mcp_handler.httpx.post")
    def test_api_relay_merges_common_and_capability_headers(self, mock_post, client, db, api_relay_setup):
        """Both app common headers and capability-specific headers are forwarded to the API."""
        mock_post.return_value = _make_json_response({"ok": True}, headers={"content-type": "application/json"})

        _tools_call(client, "api-relay", "api-relay_WeatherApp:get_weather", {"city": "Osaka"})

        sent_headers = mock_post.call_args.kwargs["headers"]
        assert sent_headers.get("X-Common") == "common-value"
        assert sent_headers.get("X-Cap") == "cap-value"


# ---------------------------------------------------------------------------
# 2. MCP relay (HTTP): MCP client -> AccelMCP -> MCP server
# ---------------------------------------------------------------------------


class TestMcpHttpRelay:
    @patch("app.services.mcp_handler.httpx.post")
    def test_mcp_relay_does_not_log_secrets_or_request_data(self, mock_post, client, db, mcp_relay_setup, caplog):
        secret_values = ["header-secret-marker", "url-secret-marker", "session-secret-marker", "body-secret-marker"]
        mcp_relay_setup["app"].mcp_url = f"https://upstream.example.com/mcp?token={secret_values[1]}"
        mcp_relay_setup["app"].common_headers = json.dumps({"Authorization": f"Bearer {secret_values[0]}"})
        db.session.commit()

        init_resp = _make_json_response({"result": {}}, headers={"Mcp-Session-Id": secret_values[2]})
        call_resp = _make_json_response(
            {"jsonrpc": "2.0", "id": 1, "result": {"content": [{"type": "text", "text": secret_values[3]}]}}
        )
        mock_post.side_effect = [init_resp, call_resp]

        with caplog.at_level(logging.DEBUG, logger="app.services.mcp_handler"):
            response = _tools_call(
                client,
                "mcp-relay",
                "mcp-relay_UpstreamMcp:remote_search",
                {"query": "argument-secret-marker"},
            )

        assert response.status_code == 200
        for secret_value in [*secret_values, "argument-secret-marker"]:
            assert secret_value not in caplog.text

    @patch("app.services.mcp_handler.httpx.post")
    def test_mcp_relay_tool_call_success(self, mock_post, client, db, mcp_relay_setup):
        """tools/call on an mcp_tool capability initializes a session then relays tools/call upstream."""
        # 1st POST = initialize (returns a session id), 2nd POST = tools/call
        init_resp = _make_json_response(
            {"jsonrpc": "2.0", "id": 0, "result": {"protocolVersion": "2024-11-05"}},
            headers={"Mcp-Session-Id": "upstream-session-xyz"},
        )
        call_resp = _make_json_response(
            {"jsonrpc": "2.0", "id": 1, "result": {"content": [{"type": "text", "text": "relayed-result"}]}}
        )
        mock_post.side_effect = [init_resp, call_resp]

        resp = _tools_call(client, "mcp-relay", "mcp-relay_UpstreamMcp:remote_search", {"query": "hello"})
        assert resp.status_code == 200
        data = json.loads(resp.data)

        # The upstream CallToolResult is relayed as-is instead of being re-wrapped as JSON text
        assert data["result"]["content"][0]["text"] == "relayed-result"
        assert data["result"]["isError"] is False

        # initialize + tools/call = 2 upstream calls
        assert mock_post.call_count == 2

    @patch("app.services.mcp_handler.httpx.post")
    def test_mcp_relay_forwards_tool_name_and_arguments(self, mock_post, client, db, mcp_relay_setup):
        """The relayed upstream request uses the capability name and the caller's arguments."""
        init_resp = _make_json_response({"result": {}}, headers={})
        call_resp = _make_json_response({"jsonrpc": "2.0", "id": 1, "result": {"content": []}})
        mock_post.side_effect = [init_resp, call_resp]

        _tools_call(client, "mcp-relay", "mcp-relay_UpstreamMcp:remote_search", {"query": "abc"})

        # Inspect the second (tools/call) upstream request body
        second_call = mock_post.call_args_list[1]
        sent_body = second_call.kwargs["json"]
        assert sent_body["method"] == "tools/call"
        assert sent_body["params"]["name"] == "remote_search"
        assert sent_body["params"]["arguments"] == {"query": "abc"}

    @patch("app.services.mcp_handler.httpx.post")
    def test_mcp_relay_forwards_common_headers(self, mock_post, client, db, mcp_relay_setup):
        """App common headers (e.g. upstream auth) are forwarded to the upstream MCP server."""
        init_resp = _make_json_response({"result": {}}, headers={})
        call_resp = _make_json_response({"jsonrpc": "2.0", "id": 1, "result": {"content": []}})
        mock_post.side_effect = [init_resp, call_resp]

        _tools_call(client, "mcp-relay", "mcp-relay_UpstreamMcp:remote_search", {"query": "x"})

        sent_headers = mock_post.call_args_list[0].kwargs["headers"]
        assert sent_headers.get("Authorization") == "Bearer upstream-token"

    @patch("app.services.mcp_handler.httpx.post")
    def test_mcp_relay_advertises_streamable_http_accept(self, mock_post, client, db, mcp_relay_setup):
        """AccelMCP acts as a Streamable HTTP client: it sends Accept including text/event-stream
        so it can connect to upstream servers (incl. another AccelMCP) that speak Streamable HTTP."""
        init_resp = _make_json_response({"result": {}}, headers={})
        call_resp = _make_json_response({"jsonrpc": "2.0", "id": 1, "result": {"content": []}})
        mock_post.side_effect = [init_resp, call_resp]

        _tools_call(client, "mcp-relay", "mcp-relay_UpstreamMcp:remote_search", {"query": "x"})

        for call in mock_post.call_args_list:
            accept = call.kwargs["headers"].get("Accept", "")
            assert "text/event-stream" in accept

    @patch("app.services.mcp_handler.httpx.post")
    def test_mcp_relay_parses_upstream_sse_response(self, mock_post, client, db, mcp_relay_setup):
        """When the upstream MCP server answers with an SSE (Streamable HTTP) stream, AccelMCP
        parses the data: event instead of failing on response.json()."""
        init_resp = _make_sse_response(
            {"jsonrpc": "2.0", "id": 0, "result": {"protocolVersion": "2024-11-05"}},
            headers={"Mcp-Session-Id": "sse-session-1"},
        )
        call_resp = _make_sse_response(
            {"jsonrpc": "2.0", "id": 1, "result": {"content": [{"type": "text", "text": "sse-relayed"}]}}
        )
        mock_post.side_effect = [init_resp, call_resp]

        resp = _tools_call(client, "mcp-relay", "mcp-relay_UpstreamMcp:remote_search", {"query": "hi"})
        assert resp.status_code == 200
        data = json.loads(resp.data)

        assert data["result"]["content"][0]["text"] == "sse-relayed"
        assert mock_post.call_count == 2


# ---------------------------------------------------------------------------
# 3. Daisy-chain (連結): MCP client -> AccelMCP -> AccelMCP -> MCP server
# ---------------------------------------------------------------------------


class TestDaisyChain:
    @patch("app.services.mcp_handler.httpx.post")
    def test_depth_header_is_incremented_and_propagated(self, mock_post, client, db, mcp_relay_setup):
        """An incoming X-AccelMCP-Depth is incremented before being forwarded upstream,
        so the next AccelMCP in the chain can keep counting."""
        init_resp = _make_json_response({"result": {}}, headers={})
        call_resp = _make_json_response({"jsonrpc": "2.0", "id": 1, "result": {"content": []}})
        mock_post.side_effect = [init_resp, call_resp]

        _tools_call(
            client,
            "mcp-relay",
            "mcp-relay_UpstreamMcp:remote_search",
            {"query": "x"},
            headers={"X-AccelMCP-Depth": "3"},
        )

        for call in mock_post.call_args_list:
            assert call.kwargs["headers"]["X-AccelMCP-Depth"] == "4"

    @patch("app.services.mcp_handler.httpx.post")
    def test_default_depth_starts_at_one(self, mock_post, client, db, mcp_relay_setup):
        """With no incoming depth header, the forwarded depth starts at 1."""
        init_resp = _make_json_response({"result": {}}, headers={})
        call_resp = _make_json_response({"jsonrpc": "2.0", "id": 1, "result": {"content": []}})
        mock_post.side_effect = [init_resp, call_resp]

        _tools_call(client, "mcp-relay", "mcp-relay_UpstreamMcp:remote_search", {"query": "x"})

        assert mock_post.call_args_list[0].kwargs["headers"]["X-AccelMCP-Depth"] == "1"

    @patch("app.services.mcp_handler.httpx.post")
    def test_max_depth_exceeded_aborts_without_upstream_call(self, mock_post, client, db, mcp_relay_setup):
        """At the max daisy-chain depth, the relay is refused and no upstream call is made
        (loop / runaway-chain protection)."""
        resp = _tools_call(
            client,
            "mcp-relay",
            "mcp-relay_UpstreamMcp:remote_search",
            {"query": "x"},
            headers={"X-AccelMCP-Depth": "10"},
        )
        assert resp.status_code == 200
        data = json.loads(resp.data)

        text = data["result"]["content"][0]["text"]
        inner = json.loads(text)
        assert inner["success"] is False
        assert "depth" in inner["error"].lower()

        # No upstream HTTP call should have happened
        assert mock_post.call_count == 0


# ---------------------------------------------------------------------------
# 4. Streamable HTTP (SSE) on the main /mcp endpoint
# ---------------------------------------------------------------------------


@pytest.fixture
def streamable_setup(db):
    mcp_service = McpService(
        name="Streamable MCP",
        identifier="streamable",
        routing_type="subdomain",
        access_control="public",
        is_enabled=True,
    )
    db.session.add(mcp_service)
    db.session.commit()

    app = Service(
        name="StreamApp",
        service_type="api",
        mcp_url="https://api.example.com",
        mcp_service_id=mcp_service.id,
        is_enabled=True,
        access_control="public",
    )
    db.session.add(app)
    db.session.commit()

    cap = Capability(
        name="ping",
        description="ping tool",
        capability_type="tool",
        app_id=app.id,
        url="https://api.example.com/ping",
        headers="{}",
        body_params="{}",
        is_enabled=True,
        access_control="public",
    )
    db.session.add(cap)
    db.session.commit()
    return {"mcp_service": mcp_service, "app": app, "cap": cap}


def _sse_initialize(client, subdomain):
    return client.post(
        f"/mcp?subdomain={subdomain}",
        data=json.dumps(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {"protocolVersion": "2025-03-26", "capabilities": {}, "clientInfo": {"name": "t"}},
            }
        ),
        headers={"Content-Type": "application/json", "Accept": "text/event-stream"},
    )


def _parse_sse(resp):
    """Extract the JSON object from an SSE 'data: <json>\\n\\n' body."""
    body = resp.data.decode()
    assert body.startswith("data: ")
    return json.loads(body[len("data: ") :].strip())


class TestStreamableHttp:
    def test_initialize_returns_sse_with_session(self, client, db, streamable_setup):
        """An initialize request with Accept: text/event-stream gets an SSE response,
        a Mcp-Session-Id header, and a sessionId in the payload."""
        resp = _sse_initialize(client, "streamable")
        assert resp.status_code == 200
        assert "text/event-stream" in resp.content_type

        session_id = resp.headers.get("Mcp-Session-Id")
        assert session_id is not None

        payload = _parse_sse(resp)
        assert payload["result"]["sessionId"] == session_id

    @pytest.mark.parametrize("accept", ["text/event-stream", "application/json"])
    def test_subsequent_request_rejects_unknown_session(self, client, db, streamable_setup, accept):
        """A request carrying a forged Mcp-Session-Id is rejected (400) regardless of Accept.

        Requests without the header are allowed for 2026-07-28 stateless clients
        (see test_mcp_stateless.py).
        """
        resp = client.post(
            "/mcp?subdomain=streamable",
            data=json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}),
            headers={"Content-Type": "application/json", "Accept": accept, "Mcp-Session-Id": "forged"},
        )
        assert resp.status_code == 400
        data = json.loads(resp.data)
        assert data["error"]["code"] == -32600
        assert "session" in data["error"]["message"].lower()

    def test_session_roundtrip_allows_followup_request(self, client, db, streamable_setup):
        """After initialize establishes a session, a follow-up SSE request with that
        session id succeeds and is returned as an SSE stream."""
        init_resp = _sse_initialize(client, "streamable")
        session_id = init_resp.headers["Mcp-Session-Id"]

        resp = client.post(
            "/mcp?subdomain=streamable",
            data=json.dumps({"jsonrpc": "2.0", "id": 3, "method": "tools/list", "params": {}}),
            headers={
                "Content-Type": "application/json",
                "Accept": "text/event-stream",
                "Mcp-Session-Id": session_id,
            },
        )
        assert resp.status_code == 200
        assert "text/event-stream" in resp.content_type
        payload = _parse_sse(resp)
        assert "tools" in payload["result"]

    def test_get_with_sse_accept_returns_405(self, client, db, streamable_setup):
        """A GET with Accept: text/event-stream (server-push stream) is not supported -> 405."""
        resp = client.get(
            "/mcp?subdomain=streamable",
            headers={"Accept": "text/event-stream"},
        )
        assert resp.status_code == 405

    def test_delete_terminates_session(self, client, db, streamable_setup):
        """DELETE with a valid session id terminates it (200); deleting again is 404."""
        init_resp = _sse_initialize(client, "streamable")
        session_id = init_resp.headers["Mcp-Session-Id"]

        resp = client.delete(
            "/mcp?subdomain=streamable",
            headers={"Mcp-Session-Id": session_id},
        )
        assert resp.status_code == 200

        resp2 = client.delete(
            "/mcp?subdomain=streamable",
            headers={"Mcp-Session-Id": session_id},
        )
        assert resp2.status_code == 404

    def test_plain_json_still_works_without_sse(self, client, db, streamable_setup):
        """Backward-compat: a normal JSON POST (no Accept: text/event-stream) returns plain JSON."""
        resp = client.post(
            "/mcp?subdomain=streamable",
            data=json.dumps({"jsonrpc": "2.0", "id": 4, "method": "tools/list", "params": {}}),
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 200
        assert "application/json" in resp.content_type
        data = json.loads(resp.data)
        assert "tools" in data["result"]


# ---------------------------------------------------------------------------
# 4b. Streamable HTTP sessions backed by Redis (multi-replica / multi-host)
# ---------------------------------------------------------------------------


class TestStreamableHttpRedisSession:
    """The Streamable HTTP session must survive when stored in Redis, so that the MCP
    endpoint can be scaled across replicas/hosts (a follow-up request handled by another
    replica still recognizes the session)."""

    def test_session_roundtrip_with_redis_backend(self, client, db, streamable_setup, monkeypatch):
        import fakeredis

        from app.services import session_store

        # Force the Redis backend with a shared in-process fake server
        shared = fakeredis.FakeStrictRedis(decode_responses=True)
        monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
        monkeypatch.setattr("redis.from_url", lambda url, **kw: shared)
        session_store.reset_session_stores()
        try:
            # initialize -> session created in Redis
            init = _sse_initialize(client, "streamable")
            session_id = init.headers["Mcp-Session-Id"]
            payload = _parse_sse(init)
            assert payload["result"]["sessionId"] == session_id

            # The session key is actually present in the (fake) Redis store
            assert shared.exists(f"accelmcp:session:mcp:{session_id}") == 1

            # A follow-up SSE request validates against Redis and succeeds
            resp = client.post(
                "/mcp?subdomain=streamable",
                data=json.dumps({"jsonrpc": "2.0", "id": 3, "method": "tools/list", "params": {}}),
                headers={
                    "Content-Type": "application/json",
                    "Accept": "text/event-stream",
                    "Mcp-Session-Id": session_id,
                },
            )
            assert resp.status_code == 200
            assert "tools" in _parse_sse(resp)["result"]

            # DELETE removes it from Redis
            client.delete("/mcp?subdomain=streamable", headers={"Mcp-Session-Id": session_id})
            assert shared.exists(f"accelmcp:session:mcp:{session_id}") == 0
        finally:
            session_store.reset_session_stores()


# ---------------------------------------------------------------------------
# 5. Path-based routing relay (連結 also works over path routing)
# ---------------------------------------------------------------------------


class TestPathRoutingRelay:
    @patch("app.services.mcp_handler.httpx.post")
    def test_api_relay_over_path_routing(self, mock_post, client, db):
        """API relay works through the path-based endpoint /<identifier>/mcp as well."""
        mcp_service = McpService(
            name="Path Relay",
            identifier="path-relay",
            routing_type="path",
            access_control="public",
            is_enabled=True,
        )
        db.session.add(mcp_service)
        db.session.commit()

        app = Service(
            name="PathApp",
            service_type="api",
            mcp_url="https://api.example.com",
            mcp_service_id=mcp_service.id,
            is_enabled=True,
            access_control="public",
        )
        db.session.add(app)
        db.session.commit()

        cap = Capability(
            name="echo",
            capability_type="tool",
            app_id=app.id,
            url="https://api.example.com/echo",
            headers="{}",
            body_params='{"properties": {"msg": {"type": "string"}}, "required": []}',
            is_enabled=True,
            access_control="public",
        )
        db.session.add(cap)
        db.session.commit()

        mock_post.return_value = _make_json_response({"echo": "hi"}, headers={"content-type": "application/json"})

        resp = client.post(
            "/path-relay/mcp",
            data=json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tools/call",
                    "params": {"name": "path-relay_PathApp:echo", "arguments": {"msg": "hi"}},
                }
            ),
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 200
        data = json.loads(resp.data)
        text = data["result"]["content"][0]["text"]
        inner = json.loads(text)
        assert inner["success"] is True
        assert inner["data"]["echo"] == "hi"


class TestRelayBehavior:
    @patch("app.services.mcp_handler.httpx.post")
    def test_mcp_relay_resolves_variables_in_headers_and_url(self, mock_post, client, db, mcp_relay_setup):
        from app.models.models import Variable

        variable = Variable(name="UPSTREAM_TOKEN", value_type="string", source_type="value")
        variable.set_value("resolved-token")
        db.session.add(variable)
        mcp_relay_setup["app"].mcp_url = "https://upstream.example.com/mcp?key={{UPSTREAM_TOKEN}}"
        mcp_relay_setup["app"].common_headers = '{"Authorization": "Bearer {{UPSTREAM_TOKEN}}"}'
        db.session.commit()
        mock_post.side_effect = [
            _make_json_response({"jsonrpc": "2.0", "id": 0, "result": {}}),
            _make_json_response({"jsonrpc": "2.0", "id": 1, "result": {"content": []}}),
        ]

        _tools_call(client, "mcp-relay", "mcp-relay_UpstreamMcp:remote_search", {"query": "q"})

        for call in mock_post.call_args_list:
            assert call.args[0] == "https://upstream.example.com/mcp?key=resolved-token"
            assert call.kwargs["headers"]["Authorization"] == "Bearer resolved-token"

    @patch("app.services.mcp_handler.httpx.post")
    def test_upstream_jsonrpc_error_is_reported_as_tool_error(self, mock_post, client, db, mcp_relay_setup):
        mock_post.side_effect = [
            _make_json_response({"jsonrpc": "2.0", "id": 0, "result": {}}),
            _make_json_response({"jsonrpc": "2.0", "id": 1, "error": {"code": -32602, "message": "bad args"}}),
        ]

        resp = _tools_call(client, "mcp-relay", "mcp-relay_UpstreamMcp:remote_search", {"query": "q"})

        result = json.loads(resp.data)["result"]
        assert result["isError"] is True
        assert result["content"][0]["text"] == "bad args"

    @patch("app.services.mcp_handler.httpx.post")
    def test_upstream_transport_failure_is_reported_as_tool_error(self, mock_post, client, db, mcp_relay_setup):
        mock_post.side_effect = ConnectionError("upstream down")

        resp = _tools_call(client, "mcp-relay", "mcp-relay_UpstreamMcp:remote_search", {"query": "q"})

        assert json.loads(resp.data)["result"]["isError"] is True

    def test_stdio_call_times_out(self, db, mcp_relay_setup):
        import asyncio

        from app.services.mcp_handler import MCPHandler

        app = mcp_relay_setup["app"]
        app.mcp_transport = "stdio"
        app.stdio_command = "fake-server"
        cap = mcp_relay_setup["cap"]
        cap.timeout_seconds = 0.05
        db.session.commit()

        async def hang(*_args, **_kwargs):
            await asyncio.sleep(10)

        with patch.object(MCPHandler, "_async_stdio_mcp_call", hang):
            result = MCPHandler(db)._execute_stdio_mcp_call(app, cap, {})

        assert result["success"] is False
        assert "timed out" in result["error"]


class TestInvalidRequests:
    def test_batch_request_is_rejected(self, client, db, mcp_relay_setup):
        resp = client.post(
            "/mcp?subdomain=mcp-relay",
            data=json.dumps([{"jsonrpc": "2.0", "id": 1, "method": "tools/list"}]),
            headers={"Content-Type": "application/json"},
        )

        assert resp.status_code == 400
        assert json.loads(resp.data)["error"]["code"] == -32600

    def test_non_string_method_is_rejected(self, client, db, mcp_relay_setup):
        resp = client.post(
            "/mcp?subdomain=mcp-relay",
            data=json.dumps({"jsonrpc": "2.0", "id": 7, "method": None}),
            headers={"Content-Type": "application/json"},
        )

        assert resp.status_code == 400
        body = json.loads(resp.data)
        assert body["error"]["code"] == -32600
        assert body["id"] == 7

    def test_log_entry_without_method_is_stored_as_unknown(self, app, db):
        """Malformed JSON leaves mcp_method as None; the log row must still be written."""
        from app.models.models import McpConnectionLog
        from app.services.mcp_logger import _write_log_entry

        _write_log_entry(app, {"mcp_method": None, "status_code": 400, "is_success": False})

        assert McpConnectionLog.query.filter_by(mcp_method="unknown").count() == 1


class TestApiCallBehavior:
    @patch("app.services.mcp_handler.httpx.post")
    def test_const_params_win_over_arguments(self, mock_post, client, db, api_relay_setup):
        api_relay_setup["cap"].body_params = json.dumps(
            {"properties": {"city": {"type": "string"}, "units": {"type": "string", "const": "metric"}}}
        )
        db.session.commit()
        mock_post.return_value = _make_json_response({"ok": True})

        _tools_call(client, "api-relay", "api-relay_WeatherApp:get_weather", {"city": "Osaka", "units": "imperial"})

        assert mock_post.call_args.kwargs["json"] == {"units": "metric", "city": "Osaka"}

    @patch("app.services.mcp_handler.httpx.post")
    def test_broken_body_params_still_sends_arguments(self, mock_post, client, db, api_relay_setup):
        api_relay_setup["cap"].body_params = "{not json"
        db.session.commit()
        mock_post.return_value = _make_json_response({"ok": True})

        _tools_call(client, "api-relay", "api-relay_WeatherApp:get_weather", {"city": "Osaka"})

        assert mock_post.call_args.kwargs["json"] == {"city": "Osaka"}

    @patch("app.services.mcp_handler.httpx.post")
    def test_error_details_do_not_contain_resolved_secrets(self, mock_post, client, db, api_relay_setup):
        import httpx

        from app.models.models import Variable

        variable = Variable(name="WEATHER_KEY", value_type="string", source_type="value")
        variable.set_value("resolved-secret-123")
        db.session.add(variable)
        api_relay_setup["cap"].url = "https://api.example.com/weather?key={{WEATHER_KEY}}"
        db.session.commit()
        mock_post.side_effect = httpx.TimeoutException("timed out")

        resp = _tools_call(client, "api-relay", "api-relay_WeatherApp:get_weather", {"city": "Osaka"})

        assert mock_post.call_args.args[0] == "https://api.example.com/weather?key=resolved-secret-123"
        body = resp.get_data(as_text=True)
        assert "resolved-secret-123" not in body
        assert json.loads(resp.data)["result"]["isError"] is True
