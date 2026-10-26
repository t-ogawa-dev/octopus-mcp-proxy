"""
Connection Test Service
Checks that an upstream MCP server (HTTP or stdio) is reachable before an App is saved
"""

import logging
import re
from typing import Any

from app.services.variable_replacer import VariableReplacer

logger = logging.getLogger(__name__)

_VARIABLE_PATTERN = re.compile(r"\{\{([A-Z0-9_]+)\}\}")


def _resolve(value: Any, unresolved: set[str]) -> str:
    """Replace {{VAR}} placeholders and remember the names that have no Variable."""
    resolved = VariableReplacer.replace_in_string(str(value))
    unresolved.update(_VARIABLE_PATTERN.findall(resolved))
    return resolved


def _unresolved_error(unresolved: set[str]) -> tuple[dict, int]:
    names = ", ".join(sorted(unresolved))
    return {"success": False, "error": f"未定義の変数: {names}。Variables画面で登録してください。"}, 400


def check_http_connection(mcp_url: str, common_headers: dict[str, Any]) -> tuple[dict, int]:
    """Send an MCP initialize request to mcp_url. Returns (response body, HTTP status)."""
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry

    unresolved: set[str] = set()
    headers = {_resolve(key, unresolved): _resolve(value, unresolved) for key, value in common_headers.items()}
    if unresolved:
        return _unresolved_error(unresolved)
    headers["Content-Type"] = "application/json"

    # Avoid logging URLs and resolved headers because they may contain credentials.
    logger.info("Testing MCP HTTP connection")

    session = requests.Session()
    adapter = HTTPAdapter(max_retries=Retry(total=2, backoff_factor=0.1))
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    init_request = {
        "jsonrpc": "2.0",
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "Octopus MCP Proxy", "version": "1.0.0"},
        },
        "id": 1,
    }

    try:
        response = session.post(mcp_url, json=init_request, headers=headers, timeout=10)
    except requests.exceptions.Timeout:
        return {"success": False, "error": "Connection timeout"}, 200
    except requests.exceptions.ConnectionError:
        return {"success": False, "error": "Cannot connect to server"}, 200
    except requests.exceptions.RequestException as e:
        return {"success": False, "error": str(e)}, 200

    content_type = response.headers.get("Content-Type", "")
    if "text/event-stream" in content_type:
        return {"success": True, "message": "Connection successful (SSE)", "server_type": "sse"}, 200

    if response.status_code == 405:
        return {
            "success": False,
            "error": "Method Not Allowed (405). The endpoint may not support MCP protocol "
            "or requires different authentication.",
        }, 200
    if response.status_code != 200:
        return {
            "success": False,
            "error": f"Server returned status code {response.status_code}: {response.text[:200]}",
        }, 200

    if not response.text or not response.text.strip():
        return {"success": False, "error": "Server returned empty response"}, 200
    try:
        result = response.json()
    except ValueError as e:
        # Do not log upstream response content, which may contain credentials.
        logger.warning(
            "Non-JSON response from MCP connection test (status=%s, content_type=%s)",
            response.status_code,
            content_type,
        )
        return {"success": False, "error": f"Invalid JSON response: {e}. Content-Type: {content_type}"}, 200

    if "result" in result:
        server_info = result.get("result", {}).get("serverInfo", {})
        return {"success": True, "message": "Connection successful", "server_info": server_info}, 200
    if "error" in result:
        error_msg = result["error"].get("message", "Unknown error")
        error_code = result["error"].get("code", "unknown")
        return {"success": False, "error": f"MCP Error ({error_code}): {error_msg}"}, 200
    return {"success": True, "message": "Connection successful (non-standard response)"}, 200


def check_stdio_connection(command: str, args: list[Any], env: dict[str, Any], cwd: str | None) -> tuple[dict, int]:
    """Start the stdio MCP server and list its tools. Returns (response body, HTTP status)."""
    # Resolved through the module so tests can patch the connection function
    from app.services import mcp_discovery

    unresolved: set[str] = set()
    resolved_args = [_resolve(arg, unresolved) for arg in args]
    resolved_env = {key: _resolve(value, unresolved) for key, value in env.items()}
    if unresolved:
        return _unresolved_error(unresolved)

    # Args and env may contain resolved secrets, so neither is logged
    logger.info("Testing stdio MCP connection")
    try:
        result = mcp_discovery.test_stdio_mcp_connection(command, resolved_args, resolved_env, cwd)
    except Exception as e:
        logger.error("Stdio connection test failed (%s)", type(e).__name__)
        return {"success": False, "error": str(e)}, 200

    if not result.get("success"):
        return {"success": False, "error": result.get("error", "Unknown error")}, 200
    return {
        "success": True,
        "message": "Connection successful",
        "tools": result.get("tools", []),
        "server_info": result.get("server_info", {}),
    }, 200
