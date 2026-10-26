"""
MCP Controller
Handles MCP protocol endpoints
"""

import json
import logging

from flask import Blueprint, Response, current_app, jsonify, request

from app.models.models import ConnectionAccount, McpService, db
from app.services.mcp_handler import MCPHandler
from app.services.mcp_logger import create_log_context_from_request, log_mcp_request
from app.services.session_store import get_session_store

mcp_bp = Blueprint("mcp", __name__)
logger = logging.getLogger(__name__)

# Initialize MCP handler
mcp_handler = MCPHandler(db)


def get_subdomain_from_request():
    """Extract subdomain from request host"""
    host = request.host.split(":")[0]  # Remove port if present

    # Handle lvh.me domain (subdomain.lvh.me)
    if ".lvh.me" in host:
        subdomain_from_host = host.replace(".lvh.me", "")
        logger.debug(f"Extracted subdomain from lvh.me: {subdomain_from_host}")
        return subdomain_from_host if subdomain_from_host else None

    # Handle localhost with subdomain parameter
    subdomain: str | None = request.args.get("subdomain") or request.headers.get("X-Subdomain")
    logger.debug(f"Extracted subdomain from param/header: {subdomain}")
    return subdomain


def authenticate_bearer_token(log_context=None):
    """
    Authenticate connection account from Bearer token

    Args:
        log_context: Optional LogContext to log authentication failures
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        logger.warning("Missing or invalid Authorization header")

        # Log authentication failure
        if log_context:
            log_mcp_request(
                current_app._get_current_object(),
                log_context,
                response_body=json.dumps({"error": "Missing or invalid Authorization header"}),
                status_code=401,
                is_success=False,
                error_message="Missing or invalid Authorization header",
            )

        return None, {"error": "Missing or invalid Authorization header"}, 401

    bearer_token = auth_header[7:]  # Remove 'Bearer ' prefix
    account = ConnectionAccount.query.filter_by(bearer_token=bearer_token).first()

    if not account:
        logger.warning("Invalid bearer token")

        # Log authentication failure
        if log_context:
            log_mcp_request(
                current_app._get_current_object(),
                log_context,
                response_body=json.dumps({"error": "Invalid bearer token"}),
                status_code=401,
                is_success=False,
                error_message="Invalid bearer token",
            )

        return None, {"error": "Invalid bearer token"}, 401

    logger.debug(f"Authenticated account: {account.name}")
    return account, None, None


def _is_streamable_http_request(req) -> bool:
    """Check whether the client requests StreamableHTTP (SSE) transport."""
    accept = req.headers.get("Accept", "")
    return "text/event-stream" in accept


def _build_sse_response(data: dict, session_id: str | None = None) -> Response:
    """Wrap a JSON-RPC dict in an SSE response body.

    Format per MCP StreamableHTTP spec:
        data: <JSON>\\n\\n
    """
    body = "data: " + json.dumps(data, ensure_ascii=False) + "\n\n"
    headers = {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no",
    }
    if session_id:
        headers["Mcp-Session-Id"] = session_id
    return Response(body, status=200, headers=headers)


# Streamable HTTP session store. Backed by Redis when REDIS_URL is set (so the MCP
# endpoint can be scaled across replicas/hosts), otherwise process-local in-memory.
_SESSION_TTL_SECONDS = 3600  # 1 hour

# Methods a 2026-07-28 client may send without an established session
_STATELESS_METHODS = frozenset({"initialize", "server/discover"})


def _register_session(session_id: str) -> None:
    """Register a new StreamableHTTP session ID with expiry."""
    get_session_store("mcp").register(session_id, _SESSION_TTL_SECONDS)


def _is_valid_session(session_id: str) -> bool:
    """Return True if the session ID was issued by this server and has not expired."""
    return get_session_store("mcp").is_valid(session_id)


def _remove_session(session_id: str) -> None:
    """Terminate a StreamableHTTP session."""
    get_session_store("mcp").remove(session_id)


def _build_capabilities_response(account, mcp_service) -> dict:
    """Build the GET /mcp body from the same permission-filtered list as tools/list."""
    tools_response = mcp_handler.handle_mcp_service_request(
        account, mcp_service, {"jsonrpc": "2.0", "id": 0, "method": "tools/list"}
    )
    tools = tools_response.get("result", {}).get("tools", [])
    return {"capabilities": {"tools": tools}, "serverInfo": {"name": mcp_service.name, "version": "1.0.0"}}


def _parse_mcp_request(log_context):
    """Read the JSON-RPC body of a POST and copy its metadata into the log context.

    Returns the parsed body (None when it is not valid JSON) and the JSON-RPC id.
    """
    if request.method != "POST":
        log_context.mcp_method = request.method  # "GET", "DELETE", etc.
        return None, None

    # silent=True only suppresses JSON parse errors; oversized bodies still raise 413
    mcp_request = request.get_json(silent=True)
    if not isinstance(mcp_request, dict):
        return mcp_request, None

    request_id = mcp_request.get("id")
    log_context.request_id = str(request_id) if request_id is not None else None
    log_context.mcp_method = mcp_request.get("method", "unknown")
    log_context.request_body = json.dumps(mcp_request, ensure_ascii=False)

    # Extract tool name for tools/call
    if log_context.mcp_method == "tools/call":
        params = mcp_request.get("params") or {}
        log_context.tool_name = params.get("name") if isinstance(params, dict) else None
    return mcp_request, request_id


def _error_response(log_context, request_id, code: int, message: str, status: int, log_message: str | None = None):
    """Return a JSON-RPC error response and record it in the connection log."""
    error_response = {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}
    log_mcp_request(
        current_app._get_current_object(),
        log_context,
        response_body=json.dumps(error_response, ensure_ascii=False),
        status_code=status,
        is_success=False,
        error_code=code,
        error_message=log_message or message,
    )
    return jsonify(error_response), status


def _serve_mcp_service(mcp_service, log_context, mcp_request, request_id):
    """Handle an MCP request once the target MCP service has been resolved (shared by both routing styles)."""
    # Set MCP service info in log context
    log_context.mcp_service_id = mcp_service.id
    log_context.mcp_service_name = mcp_service.name
    log_context.access_control = mcp_service.access_control

    # Authenticate account - only required if access_control is 'restricted'
    account = None
    if mcp_service.access_control == "restricted":
        account, error, status = authenticate_bearer_token(log_context)
        if error:
            logger.warning("Authentication failed for MCP service %s", mcp_service.identifier)
            error_response = {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32000, "message": error["error"]}}
            # Log already recorded by authenticate_bearer_token
            return jsonify(error_response), status

        # Set account info in log context
        log_context.account_id = account.id
        log_context.account_name = account.name

    # Handle DELETE - session termination (StreamableHTTP spec)
    if request.method == "DELETE":
        session_id = request.headers.get("Mcp-Session-Id")
        if session_id and _is_valid_session(session_id):
            _remove_session(session_id)
            log_mcp_request(current_app._get_current_object(), log_context, status_code=200, is_success=True)
            return Response("", status=200)
        return Response("", status=404)

    # Handle GET request - return capabilities from all services
    if request.method == "GET":
        # StreamableHTTP clients expect a server-push SSE stream; we don't support it (spec: return 405)
        if _is_streamable_http_request(request):
            return Response("", status=405)
        response = _build_capabilities_response(account, mcp_service)
        log_mcp_request(
            current_app._get_current_object(),
            log_context,
            response_body=json.dumps(response, ensure_ascii=False),
            status_code=200,
            is_success=True,
        )
        return jsonify(response)

    # Handle POST request - process MCP request
    if not mcp_request:
        # JSON-RPC requires a null id when the request id could not be read
        return _error_response(log_context, None, -32700, "Parse error: Invalid JSON", 400)

    # JSON-RPC batches were removed from the MCP spec (2025-06-18), so only single objects are accepted
    if not isinstance(mcp_request, dict):
        return _error_response(
            log_context,
            None,
            -32600,
            "Invalid Request: batch requests are not supported",
            400,
            "Batch requests are not supported",
        )

    method = mcp_request.get("method")
    if not isinstance(method, str):
        return _error_response(log_context, request_id, -32600, "Invalid Request: method must be a string", 400)

    # 2026-07-28 stateless clients omit Mcp-Session-Id entirely; only reject stale/forged IDs.
    if method not in _STATELESS_METHODS:
        incoming_session_id = request.headers.get("Mcp-Session-Id")
        if incoming_session_id and not _is_valid_session(incoming_session_id):
            return _error_response(log_context, request_id, -32600, "Invalid Mcp-Session-Id", 400)

    # Notifications (no id, or notifications/*) get no JSON-RPC response
    if "id" not in mcp_request or method.startswith("notifications/"):
        logger.info("Received notification: %s", method)
        log_mcp_request(current_app._get_current_object(), log_context, status_code=202, is_success=True)
        return Response("", status=202, mimetype="application/json")

    # Route to MCP handler - pass mcp_service for multi-service handling
    response = mcp_handler.handle_mcp_service_request(account, mcp_service, mcp_request)

    # Determine if response is success or error
    is_success = "error" not in response
    error_code = response.get("error", {}).get("code") if not is_success else None
    error_message = response.get("error", {}).get("message") if not is_success else None

    log_mcp_request(
        current_app._get_current_object(),
        log_context,
        response_body=json.dumps(response, ensure_ascii=False),
        # JSON-RPC errors are still delivered with HTTP 200, so log the status actually sent
        status_code=200,
        is_success=is_success,
        error_code=error_code,
        error_message=error_message,
    )

    # Return SSE stream if client requests StreamableHTTP, otherwise plain JSON
    if _is_streamable_http_request(request):
        session_id = None
        if method == "initialize":
            session_id = response.get("result", {}).get("sessionId")
            if session_id:
                _register_session(session_id)
        return _build_sse_response(response, session_id=session_id)

    return jsonify(response)


@mcp_bp.route("/mcp", methods=["POST", "GET", "DELETE"])
def mcp_subdomain_endpoint():
    """
    MCP endpoint with subdomain routing
    Access: <subdomain>.lvh.me/mcp or localhost:5000/mcp?subdomain=<subdomain>

    Handles:
    - GET: Returns capabilities list for the service
    - POST: Processes MCP tool calls
    """
    logger.info("MCP request: %s %s", request.method, request.path)
    log_context = create_log_context_from_request(request)
    mcp_request, request_id = _parse_mcp_request(log_context)

    subdomain = get_subdomain_from_request()
    if not subdomain:
        logger.warning("Subdomain not specified in request")
        return _error_response(
            log_context,
            request_id,
            -32600,
            "Subdomain not specified. Use <subdomain>.lvh.me/mcp or add ?subdomain=<subdomain>",
            400,
            "Subdomain not specified",
        )

    mcp_service = McpService.query.filter_by(identifier=subdomain).first()
    if not mcp_service:
        return _error_response(
            log_context, request_id, -32001, f"MCP service not found for subdomain: {subdomain}", 404
        )

    return _serve_mcp_service(mcp_service, log_context, mcp_request, request_id)


@mcp_bp.route("/<path_identifier>/mcp", methods=["POST", "GET", "DELETE"])
def mcp_path_endpoint(path_identifier):
    """
    Path-based MCP endpoint
    Access: http://localhost:5100/<path_identifier>/mcp

    Handles:
    - GET: Returns capabilities list for the service
    - POST: Processes MCP tool calls
    """
    logger.info("MCP path-based request: %s %s", request.method, request.path)
    log_context = create_log_context_from_request(request)
    mcp_request, request_id = _parse_mcp_request(log_context)

    mcp_service = McpService.query.filter_by(identifier=path_identifier, routing_type="path").first()
    if not mcp_service:
        return _error_response(
            log_context, request_id, -32001, f"MCP service not found for path: {path_identifier}", 404
        )

    return _serve_mcp_service(mcp_service, log_context, mcp_request, request_id)
