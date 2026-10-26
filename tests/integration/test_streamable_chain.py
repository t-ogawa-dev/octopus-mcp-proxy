"""
End-to-end integration test for the AccelMCP daisy-chain over Streamable HTTP.

Topology under test (matches the product goal exactly):

    Agent (httpx, Accept: text/event-stream)
      --SSE--> AccelMCP-A  (/a/mcp, MCP relay)
        --SSE--> AccelMCP-B  (/b/mcp, MCP relay)
          --SSE--> leaf MCP service (minimal Streamable-HTTP MCP server)

Every hop is contacted with `Accept: text/event-stream`, so each AccelMCP both
*serves* Streamable HTTP and, as a client, *speaks* Streamable HTTP to the next hop.

Three real servers are started on localhost (werkzeug + a tiny Flask MCP server,
threaded). Each AccelMCP uses its own temporary SQLite file, so the two AccelMCP
instances are fully independent — this is the "two real AccelMCP instances"
end-to-end check the chain was designed for.

Run just this file:
    python -m pytest tests/integration/test_streamable_chain.py -v
"""

import contextlib
import json
import os
import tempfile
import threading
import time
from wsgiref.simple_server import WSGIRequestHandler, make_server

import httpx
import pytest
from flask import Flask, Response, request

from app import create_app
from app.config.config import Config

# ---------------------------------------------------------------------------
# Helpers to spin up real WSGI servers on localhost
# ---------------------------------------------------------------------------


class _QuietHandler(WSGIRequestHandler):
    def log_message(self, *args, **kwargs):  # silence per-request logging
        pass


class _ServerThread:
    def __init__(self, wsgi_app):
        self.server = make_server("127.0.0.1", 0, wsgi_app, handler_class=_QuietHandler)
        self.port = self.server.server_port
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    def start(self):
        self.thread.start()
        return self

    @property
    def base_url(self):
        return f"http://127.0.0.1:{self.port}"

    def stop(self):
        self.server.shutdown()
        self.server.server_close()


def _wait_until_up(url, timeout=5.0):
    deadline = time.time() + timeout
    last_err = None
    while time.time() < deadline:
        try:
            httpx.get(url, timeout=1.0)
            return
        except Exception as e:  # noqa: BLE001
            last_err = e
            time.sleep(0.05)
    raise RuntimeError(f"Server at {url} did not come up: {last_err}")


# ---------------------------------------------------------------------------
# Leaf: a minimal Streamable-HTTP MCP server (the final MCP service)
# ---------------------------------------------------------------------------


def _make_leaf_mcp():
    """A tiny MCP server that only speaks Streamable HTTP (always answers with SSE).

    tools/call echoes back its arguments plus the X-AccelMCP-Depth header it received,
    so the test can prove the daisy-chain depth was propagated all the way to the leaf.
    """
    leaf = Flask("leaf_mcp")

    def _sse(payload):
        body = "data: " + json.dumps(payload) + "\n\n"
        return Response(
            body,
            status=200,
            headers={"Content-Type": "text/event-stream", "Mcp-Session-Id": "leaf-session"},
        )

    @leaf.route("/mcp", methods=["POST"])
    def handle():
        body = request.get_json(silent=True) or {}
        method = body.get("method")
        req_id = body.get("id")
        depth = request.headers.get("X-AccelMCP-Depth")

        if method == "initialize":
            return _sse(
                {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {"tools": {}},
                        "serverInfo": {"name": "leaf-mcp", "version": "1.0.0"},
                        "sessionId": "leaf-session",
                    },
                }
            )
        if method == "tools/call":
            args = body.get("params", {}).get("arguments", {})
            return _sse(
                {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps({"echoed": args, "received_depth": depth}),
                            }
                        ]
                    },
                }
            )
        return _sse({"jsonrpc": "2.0", "id": req_id, "result": {}})

    @leaf.route("/health")
    def health():
        return {"ok": True}

    return leaf


# ---------------------------------------------------------------------------
# AccelMCP instance factory (own temp DB, seeded as an MCP relay)
# ---------------------------------------------------------------------------


def _make_accelmcp(db_path):
    class _Cfg(Config):
        TESTING = True
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{db_path}"
        WTF_CSRF_ENABLED = False
        SECRET_KEY = "integration-secret"

    return create_app(_Cfg)


def _seed_mcp_relay(app, identifier, app_name, cap_name, upstream_mcp_url):
    """Configure an AccelMCP as: MCP service -> MCP app (http) -> mcp_tool capability -> upstream_mcp_url."""
    from app.models.models import Capability, McpService, Service, db

    with app.app_context():
        db.create_all()
        svc = McpService(
            name=f"{identifier} service",
            identifier=identifier,
            routing_type="path",
            access_control="public",
            is_enabled=True,
        )
        db.session.add(svc)
        db.session.commit()

        relay_app = Service(
            name=app_name,
            service_type="mcp",
            mcp_transport="http",
            mcp_url=upstream_mcp_url,
            mcp_service_id=svc.id,
            is_enabled=True,
            access_control="public",
            common_headers="{}",
        )
        db.session.add(relay_app)
        db.session.commit()

        cap = Capability(
            name=cap_name,
            description="relay to upstream MCP",
            capability_type="mcp_tool",
            app_id=relay_app.id,
            headers="{}",
            body_params='{"properties": {"msg": {"type": "string"}}, "required": []}',
            is_enabled=True,
            access_control="public",
        )
        db.session.add(cap)
        db.session.commit()


# ---------------------------------------------------------------------------
# Fixture: build the full Agent -> A -> B -> leaf MCP chain
# ---------------------------------------------------------------------------


@pytest.fixture
def streamable_chain():
    tmp_files = []
    servers = []
    try:
        # 1) Leaf MCP service (Streamable HTTP only)
        leaf_srv = _ServerThread(_make_leaf_mcp()).start()
        servers.append(leaf_srv)
        _wait_until_up(f"{leaf_srv.base_url}/health")

        # 2) AccelMCP-B : MCP relay -> leaf MCP
        fd_b, db_b_path = tempfile.mkstemp(suffix="_b.db")
        os.close(fd_b)
        tmp_files.append(db_b_path)
        app_b = _make_accelmcp(db_b_path)
        _seed_mcp_relay(
            app_b,
            identifier="b",
            app_name="LeafApp",
            cap_name="echo",  # leaf ignores the tool name, just echoes
            upstream_mcp_url=f"{leaf_srv.base_url}/mcp",
        )
        b_srv = _ServerThread(app_b).start()
        servers.append(b_srv)
        _wait_until_up(f"{b_srv.base_url}/health")

        # 3) AccelMCP-A : MCP relay -> AccelMCP-B (/b/mcp)
        fd_a, db_a_path = tempfile.mkstemp(suffix="_a.db")
        os.close(fd_a)
        tmp_files.append(db_a_path)
        app_a = _make_accelmcp(db_a_path)
        _seed_mcp_relay(
            app_a,
            identifier="a",
            app_name="MidApp",
            cap_name="echo",  # B's tool name (matched by ':'-less lookup on B)
            upstream_mcp_url=f"{b_srv.base_url}/b/mcp",
        )
        a_srv = _ServerThread(app_a).start()
        servers.append(a_srv)
        _wait_until_up(f"{a_srv.base_url}/health")

        yield {"a": a_srv, "b": b_srv, "leaf": leaf_srv}
    finally:
        for s in reversed(servers):
            s.stop()
        for f in tmp_files:
            with contextlib.suppress(OSError):
                os.unlink(f)


def _sse_post(url, payload, session_id=None):
    headers = {"Content-Type": "application/json", "Accept": "text/event-stream"}
    if session_id:
        headers["Mcp-Session-Id"] = session_id
    return httpx.post(url, json=payload, headers=headers, timeout=10.0)


def _parse_sse(resp):
    body = resp.text
    assert body.startswith("data: "), f"not an SSE body: {body[:80]!r}"
    return json.loads(body[len("data: ") :].strip())


def _unwrap_chain_text(payload):
    """Return the leaf's echoed JSON object.

    Each AccelMCP hop relays the upstream CallToolResult unchanged, so the leaf's
    content arrives at the top level of A's response.
    """
    assert payload["result"]["isError"] is False
    return json.loads(payload["result"]["content"][0]["text"])


# ---------------------------------------------------------------------------
# The actual end-to-end tests
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestStreamableChain:
    def test_agent_streamable_initialize_against_first_hop(self, streamable_chain):
        """Agent can open a Streamable HTTP session against AccelMCP-A (first hop)."""
        a = streamable_chain["a"]
        resp = _sse_post(
            f"{a.base_url}/a/mcp",
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
        )
        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers["content-type"]
        assert resp.headers.get("Mcp-Session-Id")
        payload = _parse_sse(resp)
        assert payload["result"]["sessionId"]

    def test_full_chain_tools_call_over_streamable_http(self, streamable_chain):
        """Agent --SSE--> A --SSE--> B --SSE--> leaf MCP, end to end.

        Verifies the call reaches the leaf and the echoed payload returns all the way back.
        """
        a = streamable_chain["a"]

        init = _sse_post(
            f"{a.base_url}/a/mcp",
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
        )
        session_id = init.headers["Mcp-Session-Id"]

        resp = _sse_post(
            f"{a.base_url}/a/mcp",
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {"name": "a_MidApp:echo", "arguments": {"msg": "hello-chain"}},
            },
            session_id=session_id,
        )
        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers["content-type"]

        echoed = _unwrap_chain_text(_parse_sse(resp))
        assert echoed["echoed"]["msg"] == "hello-chain"

    def test_daisy_chain_depth_increments_across_hops(self, streamable_chain):
        """The leaf MCP should see X-AccelMCP-Depth == 2 (incremented once per AccelMCP hop:
        A sets 1 when calling B, B sets 2 when calling the leaf)."""
        a = streamable_chain["a"]
        init = _sse_post(
            f"{a.base_url}/a/mcp",
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
        )
        session_id = init.headers["Mcp-Session-Id"]

        resp = _sse_post(
            f"{a.base_url}/a/mcp",
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {"name": "a_MidApp:echo", "arguments": {"msg": "depth"}},
            },
            session_id=session_id,
        )
        echoed = _unwrap_chain_text(_parse_sse(resp))
        assert echoed["received_depth"] == "2"

    def test_second_hop_directly_also_serves_streamable_http(self, streamable_chain):
        """AccelMCP-B (the middle hop) independently serves Streamable HTTP too."""
        b = streamable_chain["b"]
        resp = _sse_post(
            f"{b.base_url}/b/mcp",
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
        )
        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers["content-type"]
        assert resp.headers.get("Mcp-Session-Id")
