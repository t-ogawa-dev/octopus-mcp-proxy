"""
Tests for Admin MCP endpoint (/admin/mcp)
"""

import json

import pytest

VALID_API_KEY = "test-admin-api-key"
BEARER = f"Bearer {VALID_API_KEY}"


@pytest.fixture(autouse=True)
def set_admin_api_key(app):
    """テスト用に ADMIN_API_KEY を設定する"""
    app.config["ADMIN_API_KEY"] = VALID_API_KEY
    yield
    app.config["ADMIN_API_KEY"] = ""


def post_admin_mcp(client, payload, headers=None):
    h = {"Content-Type": "application/json"}
    if headers:
        h.update(headers)
    return client.post("/admin/mcp", data=json.dumps(payload), headers=h)


# ---------------------------------------------------------------------------
# 認証テスト
# ---------------------------------------------------------------------------


class TestAdminMcpAuth:
    def test_missing_auth_header_returns_401(self, client, db):
        resp = post_admin_mcp(client, {"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
        assert resp.status_code == 401
        data = json.loads(resp.data)
        assert "error" in data

    def test_invalid_api_key_returns_401(self, client, db):
        resp = post_admin_mcp(
            client,
            {"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
            headers={"Authorization": "Bearer wrong-key"},
        )
        assert resp.status_code == 401

    def test_valid_api_key_accepted(self, client, db):
        resp = post_admin_mcp(
            client,
            {"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
            headers={"Authorization": BEARER},
        )
        assert resp.status_code == 200

    def test_get_without_sse_returns_200(self, client, db):
        resp = client.get("/admin/mcp", headers={"Authorization": BEARER})
        assert resp.status_code == 200

    def test_get_with_sse_returns_405(self, client, db):
        resp = client.get(
            "/admin/mcp",
            headers={"Authorization": BEARER, "Accept": "text/event-stream"},
        )
        assert resp.status_code == 405

    def test_delete_unknown_session_returns_404(self, client, db):
        resp = client.delete(
            "/admin/mcp",
            headers={"Authorization": BEARER, "Mcp-Session-Id": "nonexistent"},
        )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# initialize
# ---------------------------------------------------------------------------


class TestAdminMcpInitialize:
    def test_initialize_returns_session_id(self, client, db):
        resp = post_admin_mcp(
            client,
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {"protocolVersion": "2025-03-26", "capabilities": {}, "clientInfo": {"name": "test"}},
            },
            headers={"Authorization": BEARER},
        )
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["result"]["serverInfo"]["name"] == "Octopus MCP Proxy Admin"
        assert "sessionId" in data["result"]

    def test_initialize_sse_response(self, client, db):
        resp = post_admin_mcp(
            client,
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {},
            },
            headers={"Authorization": BEARER, "Accept": "text/event-stream"},
        )
        assert resp.status_code == 200
        assert "text/event-stream" in resp.content_type
        # SSE body: "data: {...}\n\n"
        body = resp.data.decode()
        assert body.startswith("data: ")
        payload = json.loads(body[6:].strip())
        assert "sessionId" in payload["result"]
        # Mcp-Session-Id header should be set
        assert resp.headers.get("Mcp-Session-Id") is not None


# ---------------------------------------------------------------------------
# tools/list
# ---------------------------------------------------------------------------


class TestAdminMcpToolsList:
    def test_tools_list_returns_all_tools(self, client, db):
        resp = post_admin_mcp(
            client,
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
            headers={"Authorization": BEARER},
        )
        assert resp.status_code == 200
        data = json.loads(resp.data)
        tools = data["result"]["tools"]
        tool_names = {t["name"] for t in tools}
        expected = {
            "get_dashboard_summary",
            "get_connection_logs",
            "get_error_logs",
            "get_admin_action_logs",
            "list_mcp_services",
            "create_mcp_service",
            "delete_mcp_service",
            "list_apps",
            "list_variables",
            "set_variable",
            "delete_variable",
            "list_templates",
        }
        assert expected <= tool_names


# ---------------------------------------------------------------------------
# tools/call
# ---------------------------------------------------------------------------


class TestAdminMcpToolsCall:
    def _call_tool(self, client, tool_name, arguments=None):
        return post_admin_mcp(
            client,
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {"name": tool_name, "arguments": arguments or {}},
            },
            headers={"Authorization": BEARER},
        )

    def test_get_dashboard_summary(self, client, db):
        resp = self._call_tool(client, "get_dashboard_summary")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["result"]["isError"] is False
        content = json.loads(data["result"]["content"][0]["text"])
        assert "mcp_service_count" in content

    def test_missing_required_argument_returns_invalid_params(self, client, db):
        resp = self._call_tool(client, "delete_variable", {})

        assert json.loads(resp.data)["error"]["code"] == -32602

    def test_list_mcp_services_empty(self, client, db):
        resp = self._call_tool(client, "list_mcp_services")
        assert resp.status_code == 200
        content = json.loads(json.loads(resp.data)["result"]["content"][0]["text"])
        assert content["mcp_services"] == []

    def test_create_and_list_mcp_service(self, client, db):
        # create
        resp = self._call_tool(
            client,
            "create_mcp_service",
            {"name": "Test Service", "identifier": "test-svc", "routing_type": "path"},
        )
        assert resp.status_code == 200
        content = json.loads(json.loads(resp.data)["result"]["content"][0]["text"])
        assert content["mcp_service"]["identifier"] == "test-svc"

        # list
        resp2 = self._call_tool(client, "list_mcp_services")
        content2 = json.loads(json.loads(resp2.data)["result"]["content"][0]["text"])
        assert len(content2["mcp_services"]) == 1

    def test_create_mcp_service_duplicate_identifier(self, client, db):
        self._call_tool(client, "create_mcp_service", {"name": "S1", "identifier": "dup-id"})
        resp = self._call_tool(client, "create_mcp_service", {"name": "S2", "identifier": "dup-id"})
        data = json.loads(resp.data)
        # 重複時は JSON-RPC エラー（data["error"]）が返る
        assert "error" in data
        assert data["error"]["code"] == -32000

    def test_delete_mcp_service(self, client, db):
        # create first
        resp = self._call_tool(client, "create_mcp_service", {"name": "To Delete", "identifier": "del-svc"})
        svc_id = json.loads(json.loads(resp.data)["result"]["content"][0]["text"])["mcp_service"]["id"]

        # delete
        resp2 = self._call_tool(client, "delete_mcp_service", {"mcp_service_id": svc_id})
        content = json.loads(json.loads(resp2.data)["result"]["content"][0]["text"])
        assert content["deleted"] is True

    def test_set_and_list_variable(self, client, db):
        resp = self._call_tool(client, "set_variable", {"name": "MY_KEY", "value": "secret123"})
        assert resp.status_code == 200
        content = json.loads(json.loads(resp.data)["result"]["content"][0]["text"])
        assert content["variable"]["name"] == "MY_KEY"

        resp2 = self._call_tool(client, "list_variables")
        content2 = json.loads(json.loads(resp2.data)["result"]["content"][0]["text"])
        assert any(v["name"] == "MY_KEY" for v in content2["variables"])

    def test_delete_variable(self, client, db):
        self._call_tool(client, "set_variable", {"name": "DEL_VAR", "value": "x"})
        resp = self._call_tool(client, "delete_variable", {"name": "DEL_VAR"})
        content = json.loads(json.loads(resp.data)["result"]["content"][0]["text"])
        assert content["deleted"] is True

    def test_delete_nonexistent_variable(self, client, db):
        resp = self._call_tool(client, "delete_variable", {"name": "NO_SUCH_VAR"})
        data = json.loads(resp.data)
        # エラーレスポンス（JSON-RPC error）
        assert "error" in data

    def test_unknown_tool_returns_error(self, client, db):
        resp = self._call_tool(client, "nonexistent_tool")
        data = json.loads(resp.data)
        assert "error" in data
        assert data["error"]["code"] == -32601

    def test_get_connection_logs(self, client, db):
        resp = self._call_tool(client, "get_connection_logs", {"limit": 10, "offset": 0})
        assert resp.status_code == 200
        content = json.loads(json.loads(resp.data)["result"]["content"][0]["text"])
        assert "logs" in content
        assert "total" in content

    def test_list_templates(self, client, db):
        resp = self._call_tool(client, "list_templates")
        assert resp.status_code == 200
        content = json.loads(json.loads(resp.data)["result"]["content"][0]["text"])
        assert "templates" in content


# ---------------------------------------------------------------------------
# StreamableHTTP セッション検証
# ---------------------------------------------------------------------------


class TestAdminMcpSession:
    def test_non_initialize_without_session_returns_400(self, client, db):
        resp = post_admin_mcp(
            client,
            {"jsonrpc": "2.0", "id": 4, "method": "tools/list"},
            headers={"Authorization": BEARER, "Accept": "text/event-stream"},
        )
        assert resp.status_code == 400

    def test_session_flow(self, client, db):
        # initialize → get session id
        init_resp = post_admin_mcp(
            client,
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
            headers={"Authorization": BEARER, "Accept": "text/event-stream"},
        )
        body = init_resp.data.decode()
        session_id = json.loads(body[6:].strip())["result"]["sessionId"]

        # tools/list with valid session
        list_resp = post_admin_mcp(
            client,
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
            headers={
                "Authorization": BEARER,
                "Accept": "text/event-stream",
                "Mcp-Session-Id": session_id,
            },
        )
        assert list_resp.status_code == 200

        # DELETE session
        del_resp = client.delete(
            "/admin/mcp",
            headers={"Authorization": BEARER, "Mcp-Session-Id": session_id},
        )
        assert del_resp.status_code == 200

        # After DELETE, session should be invalid
        list_resp2 = post_admin_mcp(
            client,
            {"jsonrpc": "2.0", "id": 3, "method": "tools/list"},
            headers={
                "Authorization": BEARER,
                "Accept": "text/event-stream",
                "Mcp-Session-Id": session_id,
            },
        )
        assert list_resp2.status_code == 400


# ---------------------------------------------------------------------------
# initialize の instructions フィールド
# ---------------------------------------------------------------------------


class TestAdminMcpInstructions:
    def test_initialize_has_instructions_field(self, client, db):
        """initialize レスポンスに instructions フィールドが含まれること。"""
        resp = post_admin_mcp(
            client,
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {"protocolVersion": "2025-03-26", "capabilities": {}, "clientInfo": {"name": "test"}},
            },
            headers={"Authorization": BEARER},
        )
        assert resp.status_code == 200
        data = json.loads(resp.data)
        result = data["result"]
        assert "instructions" in result, "initialize レスポンスに 'instructions' が含まれていない"

    def test_initialize_instructions_mentions_admin(self, client, db):
        """instructions の文字列に AccelMCP に関する説明が含まれること。"""
        resp = post_admin_mcp(
            client,
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {},
            },
            headers={"Authorization": BEARER},
        )
        data = json.loads(resp.data)
        instructions = data["result"]["instructions"]
        assert isinstance(instructions, str)
        assert len(instructions) > 0
        # AccelMCP administration server を示す文字列が含まれること
        assert "AccelMCP" in instructions or "administration" in instructions.lower()

    def test_initialize_instructions_mentions_key_operations(self, client, db):
        """instructions にツール操作の説明が含まれること。"""
        resp = post_admin_mcp(
            client,
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
            headers={"Authorization": BEARER},
        )
        data = json.loads(resp.data)
        instructions = data["result"]["instructions"].lower()
        # 主要操作のキーワードが含まれること
        assert any(kw in instructions for kw in ["manage", "list", "create", "delete", "variable", "log"])


# ---------------------------------------------------------------------------
# ADMIN_TOOLS の順序・英語化検証
# ---------------------------------------------------------------------------


class TestAdminToolsDefinition:
    def test_tools_are_sorted_alphabetically(self):
        """ADMIN_TOOLS がアルファベット順に並んでいること。"""
        from app.controllers.admin_mcp_controller import ADMIN_TOOLS

        names = [t["name"] for t in ADMIN_TOOLS]
        assert names == sorted(names), f"ADMIN_TOOLS がアルファベット順でない: {names}"

    def test_all_tools_have_english_description(self):
        """各ツールの description が英語（ASCII 主体）で書かれていること。"""
        from app.controllers.admin_mcp_controller import ADMIN_TOOLS

        for tool in ADMIN_TOOLS:
            desc = tool.get("description", "")
            assert desc, f"'{tool['name']}' の description が空"
            # 日本語（ひらがな・カタカナ・漢字）が含まれていないこと
            has_japanese = any("\u3000" <= ch <= "\u9fff" or "\uff00" <= ch <= "\uffef" for ch in desc)
            assert not has_japanese, f"'{tool['name']}' の description に日本語が含まれている: {desc!r}"

    def test_all_tools_have_input_schema(self):
        """各ツールに inputSchema が定義されていること。"""
        from app.controllers.admin_mcp_controller import ADMIN_TOOLS

        for tool in ADMIN_TOOLS:
            assert "inputSchema" in tool, f"'{tool['name']}' に inputSchema がない"
            schema = tool["inputSchema"]
            assert "type" in schema, f"'{tool['name']}' の inputSchema に type がない"

    def test_expected_tool_count(self):
        """ADMIN_TOOLS に 12 個のツールが存在すること。"""
        from app.controllers.admin_mcp_controller import ADMIN_TOOLS

        assert len(ADMIN_TOOLS) == 12, f"ツール数が 12 でない: {len(ADMIN_TOOLS)}"

    def test_first_tool_is_create_mcp_service(self):
        """アルファベット順先頭は create_mcp_service であること。"""
        from app.controllers.admin_mcp_controller import ADMIN_TOOLS

        assert ADMIN_TOOLS[0]["name"] == "create_mcp_service"

    def test_input_schema_properties_are_english(self):
        """inputSchema の description フィールドが英語であること。"""
        from app.controllers.admin_mcp_controller import ADMIN_TOOLS

        for tool in ADMIN_TOOLS:
            schema = tool.get("inputSchema", {})
            props = schema.get("properties", {})
            for prop_name, prop_def in props.items():
                prop_desc = prop_def.get("description", "")
                if prop_desc:
                    has_japanese = any("\u3000" <= ch <= "\u9fff" or "\uff00" <= ch <= "\uffef" for ch in prop_desc)
                    assert not has_japanese, f"'{tool['name']}.{prop_name}' の description に日本語: {prop_desc!r}"
