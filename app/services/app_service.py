"""
App Service
Creates and updates Apps (Service model) and runs MCP capability discovery for them
"""

import json
import logging
from typing import Any

from app.models.models import Service, db

logger = logging.getLogger(__name__)

# Plain columns copied as-is from a request payload on create and update
_SCALAR_FIELDS = ("name", "service_type", "mcp_url", "mcp_transport", "stdio_command", "stdio_cwd", "description")


def _encode_json_or_none(value: Any) -> str | None:
    return json.dumps(value) if value else None


def create_app_record(data: dict[str, Any], mcp_service_id: int | None) -> Service:
    """Create an App from a request payload and discover its MCP capabilities.

    Discovery failures are logged and do not fail the creation.
    """
    service = Service(
        mcp_service_id=mcp_service_id,
        name=data["name"],
        service_type=data.get("service_type", "api"),
        mcp_url=data.get("mcp_url"),
        mcp_transport=data.get("mcp_transport", "http"),
        stdio_command=data.get("stdio_command"),
        stdio_args=_encode_json_or_none(data.get("stdio_args")),
        stdio_env=_encode_json_or_none(data.get("stdio_env")),
        stdio_cwd=data.get("stdio_cwd"),
        common_headers=json.dumps(data.get("common_headers", {})),
        description=data.get("description", ""),
    )
    db.session.add(service)
    db.session.commit()

    discover_app_capabilities(service)
    return service


def update_app_record(service: Service, data: dict[str, Any]) -> Service:
    """Apply a partial update: fields missing from the payload keep their current values."""
    for field in _SCALAR_FIELDS:
        if field in data:
            setattr(service, field, data[field])
    if "common_headers" in data:
        service.common_headers = json.dumps(data["common_headers"] or {})
    if "stdio_args" in data:
        service.stdio_args = _encode_json_or_none(data["stdio_args"])
    if "stdio_env" in data:
        service.stdio_env = _encode_json_or_none(data["stdio_env"])
    db.session.commit()

    discover_app_capabilities(service)
    return service


def discover_app_capabilities(service: Service) -> int:
    """Register the tools of an MCP App as capabilities. Returns the number of tools found (0 on failure)."""
    # Resolved through the module so tests can patch the discovery functions
    from app.services import mcp_discovery

    if service.service_type != "mcp":
        return 0

    try:
        if service.mcp_transport == "stdio" and service.stdio_command:
            tool_count = mcp_discovery.discover_stdio_mcp_capabilities(
                service.id,
                service.stdio_command,
                json.loads(service.stdio_args) if service.stdio_args else [],
                json.loads(service.stdio_env) if service.stdio_env else {},
                service.stdio_cwd,
            )
        elif service.mcp_url:
            tool_count = mcp_discovery.discover_mcp_capabilities(service.id, service.mcp_url)
        else:
            tool_count = 0
    except Exception:
        # Discovery failure must not fail App registration
        logger.exception("MCP capability discovery failed for app %s", service.id)
        return 0

    logger.info("Discovered %s MCP tools for app %s", tool_count, service.id)
    return tool_count
