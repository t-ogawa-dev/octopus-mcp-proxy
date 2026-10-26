"""
Admin MCP Controller
Octopus MCP Proxy 自身を管理する MCP エンドポイント (/admin/mcp)

認証: Authorization: Bearer <ACCELMCP_ADMIN_API_KEY>
"""

import json
import logging
import uuid

from flask import Blueprint, Response, current_app, jsonify, request
from flask.typing import ResponseReturnValue

from app.services import admin_mcp_tools
from app.services.session_store import get_session_store

admin_mcp_bp = Blueprint("admin_mcp", __name__)
logger = logging.getLogger(__name__)

# StreamableHTTP セッションストア（管理 MCP 専用）。REDIS_URL があれば Redis 共有、
# なければプロセス内メモリ。"admin" 名前空間で MCP 本体のセッションとは分離される。
_SESSION_TTL = 3600  # 1 hour


# ---------------------------------------------------------------------------
# ヘルパー
# ---------------------------------------------------------------------------


def _get_admin_api_key() -> str:
    """DB のシステムアカウントから Admin MCP APIキーを取得する。
    見つからなければ config の ADMIN_API_KEY にフォールバックする。
    """
    try:
        from app.models.models import ConnectionAccount

        system_account = ConnectionAccount.query.filter_by(is_system=True).first()
        if system_account and system_account.bearer_token:
            return system_account.bearer_token
    except Exception:
        # The key source silently switching would be hard to diagnose, so record why
        logger.exception("Failed to load Admin MCP API key from the system account")
    # Fallback: env-based key (startup before first seed)
    return current_app.config.get("ADMIN_API_KEY", "")


def _authenticate_admin() -> tuple[bool, ResponseReturnValue | None]:
    """
    Authorization: Bearer <ACCELMCP_ADMIN_API_KEY> を検証する。
    成功時 (True, None)、失敗時 (False, Response) を返す。
    """
    expected_key = _get_admin_api_key()
    if not expected_key:
        logger.error("ACCELMCP_ADMIN_API_KEY is not configured")
        return False, (jsonify({"error": "Admin MCP is not configured"}), 503)

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return False, (jsonify({"error": "Missing or invalid Authorization header"}), 401)

    provided_key = auth_header[7:]
    # タイミング攻撃対策として secrets.compare_digest を使用
    import secrets

    if not secrets.compare_digest(provided_key, expected_key):
        return False, (jsonify({"error": "Invalid API key"}), 401)

    return True, None


def _is_sse_request() -> bool:
    return "text/event-stream" in request.headers.get("Accept", "")


def _sse_response(data: dict, session_id: str | None = None) -> Response:
    body = "data: " + json.dumps(data, ensure_ascii=False) + "\n\n"
    headers = {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no",
    }
    if session_id:
        headers["Mcp-Session-Id"] = session_id
    return Response(body, status=200, headers=headers)


def _register_session(sid: str) -> None:
    get_session_store("admin").register(sid, _SESSION_TTL)


def _is_valid_session(sid: str) -> bool:
    return get_session_store("admin").is_valid(sid)


def _remove_session(sid: str) -> None:
    get_session_store("admin").remove(sid)


def _make_error(req_id, code: int, message: str) -> dict:
    return {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}}


# ---------------------------------------------------------------------------
# ツールカタログ
# ---------------------------------------------------------------------------

ADMIN_TOOLS = [
    {
        "name": "create_mcp_service",
        "description": "Create a new MCP service",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Service name"},
                "identifier": {"type": "string", "description": "Unique identifier (used in URL path etc.)"},
                "routing_type": {
                    "type": "string",
                    "enum": ["subdomain", "path"],
                    "description": "Routing type (default: path)",
                    "default": "path",
                },
                "description": {"type": "string", "description": "Description", "default": ""},
                "access_control": {
                    "type": "string",
                    "enum": ["public", "restricted"],
                    "description": "Access control (default: restricted)",
                    "default": "restricted",
                },
            },
            "required": ["name", "identifier"],
        },
    },
    {
        "name": "delete_mcp_service",
        "description": "Delete an MCP service (also deletes associated apps and capabilities)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "mcp_service_id": {"type": "integer", "description": "ID of the MCP service to delete"},
            },
            "required": ["mcp_service_id"],
        },
    },
    {
        "name": "delete_variable",
        "description": "Delete a variable",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Name of the variable to delete"},
            },
            "required": ["name"],
        },
    },
    {
        "name": "get_admin_action_logs",
        "description": "Retrieve administrator action logs",
        "inputSchema": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Number of records to fetch (max 200, default 50)",
                    "default": 50,
                },
                "offset": {"type": "integer", "description": "Offset (default 0)", "default": 0},
            },
        },
    },
    {
        "name": "get_connection_logs",
        "description": "Retrieve MCP connection logs",
        "inputSchema": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Number of records to fetch (max 200, default 50)",
                    "default": 50,
                },
                "offset": {"type": "integer", "description": "Offset (default 0)", "default": 0},
            },
        },
    },
    {
        "name": "get_dashboard_summary",
        "description": "Return an Octopus MCP Proxy-wide summary (service count, app count, variable count, recent errors)",
        "inputSchema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "get_error_logs",
        "description": "Retrieve only MCP connection logs that resulted in errors",
        "inputSchema": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Number of records to fetch (max 200, default 50)",
                    "default": 50,
                },
                "offset": {"type": "integer", "description": "Offset (default 0)", "default": 0},
            },
        },
    },
    {
        "name": "list_apps",
        "description": "Return a list of apps, optionally filtered by mcp_service_id",
        "inputSchema": {
            "type": "object",
            "properties": {
                "mcp_service_id": {
                    "type": "integer",
                    "description": "MCP service ID to filter by (returns all if omitted)",
                },
            },
        },
    },
    {
        "name": "list_mcp_services",
        "description": "Return a list of all MCP services",
        "inputSchema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "list_templates",
        "description": "Return a list of MCP service templates",
        "inputSchema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "list_variables",
        "description": "Return a list of variables (values are masked)",
        "inputSchema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "set_variable",
        "description": "Create or update a variable",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Variable name"},
                "value": {"type": "string", "description": "Value"},
                "description": {"type": "string", "description": "Description", "default": ""},
                "is_secret": {
                    "type": "boolean",
                    "description": "Whether to treat as secret (default: true)",
                    "default": True,
                },
            },
            "required": ["name", "value"],
        },
    },
]

_TOOL_MAP = {t["name"]: t for t in ADMIN_TOOLS}


# ---------------------------------------------------------------------------
# ツール呼び出しディスパッチ
# ---------------------------------------------------------------------------


def _dispatch_tool(name: str, arguments: dict) -> dict:
    """ツール名に応じて admin_mcp_tools の関数を呼び出す"""
    if name == "get_dashboard_summary":
        return admin_mcp_tools.get_dashboard_summary()
    elif name == "get_connection_logs":
        return admin_mcp_tools.get_connection_logs(
            limit=int(arguments.get("limit", 50)),
            offset=int(arguments.get("offset", 0)),
        )
    elif name == "get_error_logs":
        return admin_mcp_tools.get_error_logs(
            limit=int(arguments.get("limit", 50)),
            offset=int(arguments.get("offset", 0)),
        )
    elif name == "get_admin_action_logs":
        return admin_mcp_tools.get_admin_action_logs(
            limit=int(arguments.get("limit", 50)),
            offset=int(arguments.get("offset", 0)),
        )
    elif name == "list_mcp_services":
        return admin_mcp_tools.list_mcp_services()
    elif name == "create_mcp_service":
        return admin_mcp_tools.create_mcp_service(
            name=arguments["name"],
            identifier=arguments["identifier"],
            routing_type=arguments.get("routing_type", "path"),
            description=arguments.get("description", ""),
            access_control=arguments.get("access_control", "restricted"),
        )
    elif name == "delete_mcp_service":
        return admin_mcp_tools.delete_mcp_service(mcp_service_id=int(arguments["mcp_service_id"]))
    elif name == "list_apps":
        mcp_service_id = arguments.get("mcp_service_id")
        return admin_mcp_tools.list_apps(mcp_service_id=int(mcp_service_id) if mcp_service_id is not None else None)
    elif name == "list_variables":
        return admin_mcp_tools.list_variables()
    elif name == "set_variable":
        return admin_mcp_tools.set_variable(
            name=arguments["name"],
            value=arguments["value"],
            description=arguments.get("description", ""),
            is_secret=bool(arguments.get("is_secret", True)),
        )
    elif name == "delete_variable":
        return admin_mcp_tools.delete_variable(name=arguments["name"])
    elif name == "list_templates":
        return admin_mcp_tools.list_templates()
    else:
        return {"error": f"Unknown tool: {name}"}


# ---------------------------------------------------------------------------
# MCP リクエストハンドラ
# ---------------------------------------------------------------------------


def _handle_request(mcp_request: dict) -> tuple[dict, str | None]:
    """
    MCP リクエストを処理し (response_dict, session_id_to_set) を返す。
    session_id_to_set は initialize の場合のみ設定される。
    """
    method = mcp_request.get("method")
    req_id = mcp_request.get("id")

    if method == "initialize":
        session_id = str(uuid.uuid4())
        _register_session(session_id)
        response = {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2025-03-26",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "Octopus MCP Proxy Admin", "version": "1.0.0"},
                "instructions": (
                    "This is the Octopus MCP Proxy administration server. "
                    "Use it to manage MCP services (create/delete), list apps, manage variables (list/set/delete), "
                    "retrieve connection logs and error logs, get a dashboard summary, and list templates. "
                    "Call get_dashboard_summary first to understand the current state of the system."
                ),
                "sessionId": session_id,
            },
        }
        return response, session_id

    elif method == "tools/list":
        response = {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {"tools": ADMIN_TOOLS},
        }
        return response, None

    elif method == "tools/call":
        params = mcp_request.get("params", {})
        tool_name = params.get("name")
        arguments = params.get("arguments", {})

        if tool_name not in _TOOL_MAP:
            return _make_error(req_id, -32601, f"Tool not found: {tool_name}"), None

        try:
            result = _dispatch_tool(tool_name, arguments)
        except (KeyError, ValueError, TypeError) as e:
            # Missing or wrongly typed arguments are the caller's fault, not a server error
            return _make_error(req_id, -32602, f"Invalid params: {e}"), None
        except Exception as e:
            logger.exception(f"Admin MCP tool error: {tool_name}")
            return _make_error(req_id, -32603, f"Internal error: {str(e)}"), None

        if "error" in result:
            return _make_error(req_id, -32000, result["error"]), None

        response = {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False, indent=2)}],
                "isError": False,
            },
        }
        return response, None

    else:
        return _make_error(req_id, -32601, f"Method not found: {method}"), None


# ---------------------------------------------------------------------------
# エンドポイント
# ---------------------------------------------------------------------------


@admin_mcp_bp.route("/admin/mcp", methods=["POST", "GET", "DELETE"])
def admin_mcp_endpoint():
    """Admin MCP エンドポイント。Bearer トークン認証必須。"""
    logger.info("Admin MCP request: %s %s", request.method, request.path)

    # --- 認証 ---
    ok, err_response = _authenticate_admin()
    if not ok:
        return err_response

    # --- DELETE: セッション終了 ---
    if request.method == "DELETE":
        session_id = request.headers.get("Mcp-Session-Id")
        if session_id and _is_valid_session(session_id):
            _remove_session(session_id)
            return Response("", status=200)
        return Response("", status=404)

    # --- GET: StreamableHTTP では 405 ---
    if request.method == "GET":
        if _is_sse_request():
            return Response("", status=405)
        # 非 SSE GET はシンプルにサーバー情報を返す
        return jsonify({"server": "Octopus MCP Proxy Admin MCP", "version": "1.0.0"})

    # --- POST ---
    mcp_request = request.get_json(silent=True)
    if not mcp_request:
        return jsonify(_make_error(None, -32700, "Parse error: Invalid JSON")), 400
    if not isinstance(mcp_request, dict):
        return jsonify(_make_error(None, -32600, "Invalid Request: batch requests are not supported")), 400

    req_id = mcp_request.get("id")
    method = mcp_request.get("method", "")

    # StreamableHTTP セッション検証（initialize 以外）
    if _is_sse_request() and method != "initialize":
        incoming_sid = request.headers.get("Mcp-Session-Id")
        if not incoming_sid or not _is_valid_session(incoming_sid):
            return jsonify(_make_error(req_id, -32600, "Invalid or missing Mcp-Session-Id")), 400

    # 通知は 202 で即返す
    is_notification = "id" not in mcp_request or method.startswith("notifications/")
    if is_notification:
        return Response("", status=202, mimetype="application/json")

    response, new_session_id = _handle_request(mcp_request)

    if _is_sse_request():
        return _sse_response(response, session_id=new_session_id)

    return jsonify(response)
