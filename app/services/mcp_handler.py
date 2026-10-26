"""
MCP Handler Service
Handles MCP requests with permission checking and API/MCP relay
"""

import asyncio
import json
import logging
import re
from typing import Any

import httpx
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import get_default_environment, stdio_client

logger = logging.getLogger(__name__)


class MCPHandler:
    """Handle MCP requests with permission checking and API/MCP relay"""

    def __init__(self, db):
        self.db = db

    def _convert_param_type(self, value: str, param_type: str):
        """
        Convert string value to specified type

        Args:
            value: String value (may contain {{VARIABLE}})
            param_type: Target type ('string', 'number', 'integer', 'boolean', 'object', 'array')

        Returns:
            Converted value with appropriate type
        """
        # If value contains variable placeholder, keep as string for now
        # Variable replacement happens later
        if "{{" in value and "}}" in value:
            return value

        if param_type == "integer":
            try:
                return int(value)
            except (ValueError, AttributeError):
                return value  # Keep as string if conversion fails
        elif param_type == "number":
            try:
                # Try to convert to float
                return float(value)
            except (ValueError, AttributeError):
                return value  # Keep as string if conversion fails
        elif param_type == "boolean":
            # Convert to boolean
            return value.lower() in ("true", "1", "yes", "on")
        elif param_type == "object":
            # Try to parse as JSON object
            try:
                parsed = json.loads(value)
                if isinstance(parsed, dict):
                    return parsed
                return value
            except (json.JSONDecodeError, ValueError):
                return value
        elif param_type == "array":
            # Try to parse as JSON array
            try:
                parsed = json.loads(value)
                if isinstance(parsed, list):
                    return parsed
                return value
            except (json.JSONDecodeError, ValueError):
                return value
        else:
            # Default: keep as string
            return value

    def _sanitize_tool_name(self, name: str) -> str:
        """
        Sanitize tool name to comply with Google API requirements:
        - Must start with a letter or underscore
        - Only alphanumeric, underscores, dots, colons, dashes
        - Max 64 characters
        """
        # Replace spaces and other invalid characters with underscores
        sanitized = re.sub(r"[^a-zA-Z0-9_.:+-]", "_", name)

        # Ensure it starts with a letter or underscore
        if sanitized and not re.match(r"^[a-zA-Z_]", sanitized):
            sanitized = "_" + sanitized

        # Limit to 64 characters
        return sanitized[:64]

    def _sanitized_app_name(self, app) -> str:
        """App name as used in namespaced tool names; tools/list and tools/call must agree on it"""
        sanitized = self._sanitize_tool_name(app.name) if app.name else ""
        # Fallback if sanitized name is empty or only special characters
        if not re.sub(r"[_:\-+.]", "", sanitized):
            return "app"
        return sanitized

    def handle_mcp_service_request(self, account, mcp_service, mcp_request: dict[str, Any]) -> dict[str, Any]:
        """
        Handle MCP request at MCP Service level (統合エンドポイント)

        Args:
            account: ConnectionAccount object
            mcp_service: McpService object
            mcp_request: MCP protocol request

        Returns:
            MCP protocol response
        """

        method = mcp_request.get("method")

        if method == "initialize":
            return self._handle_initialize_for_mcp_service(account, mcp_service, mcp_request)

        elif method == "server/discover":
            return self._handle_server_discover_for_mcp_service(account, mcp_service, mcp_request)

        elif method == "tools/list":
            return self._handle_tools_list_for_mcp_service(account, mcp_service, mcp_request)

        elif method == "tools/call":
            return self._handle_tool_call_for_mcp_service(account, mcp_service, mcp_request)

        elif method == "resources/list":
            return self._handle_resources_list_for_mcp_service(account, mcp_service, mcp_request)

        elif method == "resources/read":
            return self._handle_resources_read(account, mcp_service, mcp_request)

        elif method == "prompts/list":
            return self._handle_prompts_list(account, mcp_service, mcp_request)

        elif method == "prompts/get":
            return self._handle_prompts_get(account, mcp_service, mcp_request)

        else:
            return {
                "jsonrpc": "2.0",
                "id": mcp_request.get("id"),
                "error": {"code": -32601, "message": f"Method not found: {method}"},
            }

    def _check_hierarchical_access(self, account, mcp_service, app=None, capability=None) -> bool:
        """
        Check if account has access using 3-tier hierarchical model

        Access hierarchy:
        1. McpService level: Check if service.access_control=='restricted' and permission exists
        2. App level: Check if app.access_control=='restricted' and permission exists
        3. Capability level: Check if capability.access_control=='restricted' and permission exists

        Also checks is_enabled flags at each level.

        Args:
            account: ConnectionAccount object
            mcp_service: McpService object
            app: Service (App) object (optional)
            capability: Capability object (optional)

        Returns:
            True if access granted, False otherwise
        """
        from app.models.models import AccountPermission

        # Check is_enabled flags
        if not mcp_service.is_enabled:
            logger.warning(f"MCP Service {mcp_service.id} is disabled")
            return False

        if app and not app.is_enabled:
            logger.warning(f"App {app.id} is disabled")
            return False

        if capability and not capability.is_enabled:
            logger.warning(f"Capability {capability.id} is disabled")
            return False

        # Level 1: McpService access control
        if mcp_service.access_control == "restricted":
            # If restricted but no account, deny access
            if account is None:
                logger.debug("No account provided for restricted MCP Service")
                return False

            has_service_permission = (
                self.db.session.query(AccountPermission)
                .filter(AccountPermission.account_id == account.id, AccountPermission.mcp_service_id == mcp_service.id)
                .first()
                is not None
            )

            if not has_service_permission:
                logger.debug(f"Account {account.id} denied: no MCP Service permission")
                return False

        # Level 2: App access control (if checking app or capability)
        if app and app.access_control == "restricted":
            # If restricted but no account, deny access
            if account is None:
                logger.debug("No account provided for restricted App")
                return False

            has_app_permission = (
                self.db.session.query(AccountPermission)
                .filter(AccountPermission.account_id == account.id, AccountPermission.app_id == app.id)
                .first()
                is not None
            )

            if not has_app_permission:
                logger.debug(f"Account {account.id} denied: no App permission")
                return False

        # Level 3: Capability access control (if checking specific capability)
        if capability and capability.access_control == "restricted":
            # If restricted but no account, deny access
            if account is None:
                logger.debug("No account provided for restricted Capability")
                return False

            has_capability_permission = (
                self.db.session.query(AccountPermission)
                .filter(AccountPermission.account_id == account.id, AccountPermission.capability_id == capability.id)
                .first()
                is not None
            )

            if not has_capability_permission:
                logger.debug(f"Account {account.id} denied: no Capability permission")
                return False

        # Log access granted
        if account:
            logger.debug(f"Account {account.id} granted access")
        else:
            logger.debug("Public access granted (no authentication required)")
        return True

    def _advertised_capabilities(self, mcp_service) -> dict[str, Any]:
        """Advertise only the capability kinds actually registered (and enabled) under mcp_service"""
        from app.models.models import Capability, Service

        cap_types = {
            cap_type
            for (cap_type,) in self.db.session.query(Capability.capability_type)
            .join(Service)
            .filter(Service.mcp_service_id == mcp_service.id, Service.is_enabled, Capability.is_enabled)
            .distinct()
        }

        capabilities: dict[str, Any] = {}
        if cap_types & {"tool", "mcp_tool"}:
            capabilities["tools"] = {}
        if "resource" in cap_types:
            capabilities["resources"] = {}
        if "prompt" in cap_types:
            capabilities["prompts"] = {}
        return capabilities

    def _handle_initialize_for_mcp_service(self, account, mcp_service, mcp_request: dict[str, Any]) -> dict[str, Any]:
        """Handle MCP initialize request at MCP Service level"""
        import uuid

        return {
            "jsonrpc": "2.0",
            "id": mcp_request.get("id"),
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": self._advertised_capabilities(mcp_service),
                "serverInfo": {"name": f"Octopus MCP Proxy - {mcp_service.name}", "version": "1.0.0"},
                "instructions": mcp_service.description or "",
                "sessionId": str(uuid.uuid4()),
            },
        }

    def _handle_server_discover_for_mcp_service(
        self, account, mcp_service, mcp_request: dict[str, Any]
    ) -> dict[str, Any]:
        """Handle MCP 2026-07-28 server/discover at MCP Service level (stateless, no session)."""
        return {
            "jsonrpc": "2.0",
            "id": mcp_request.get("id"),
            "result": {
                # Advertise both spec versions so clients can pick the newest they support
                "protocolVersions": ["2026-07-28", "2024-11-05"],
                "capabilities": self._advertised_capabilities(mcp_service),
                "serverInfo": {"name": f"Octopus MCP Proxy - {mcp_service.name}", "version": "1.0.0"},
                "instructions": mcp_service.description or "",
            },
        }

    def _handle_tools_list_for_mcp_service(self, account, mcp_service, mcp_request: dict[str, Any]) -> dict[str, Any]:
        """Return aggregated tools list from all apps under MCP Service"""
        from app.models.models import Capability, Service

        # Check hierarchical access at MCP service level
        if not self._check_hierarchical_access(account, mcp_service):
            return {
                "jsonrpc": "2.0",
                "id": mcp_request.get("id"),
                "result": {
                    "tools": []  # Return empty if no access to MCP service
                },
            }

        # Get all apps under this MCP service
        apps = self.db.session.query(Service).filter(Service.mcp_service_id == mcp_service.id).all()

        # Aggregate tools from all apps
        all_tools = []
        for app in apps:
            # Check app-level access
            if not self._check_hierarchical_access(account, mcp_service, app=app):
                continue

            # Get all tool-type capabilities for this app (exclude resource and prompt types)
            capabilities = (
                self.db.session.query(Capability)
                .filter(
                    Capability.app_id == app.id,
                    Capability.capability_type.in_(["tool", "mcp_tool"]),
                    Capability.is_enabled,
                )
                .all()
            )

            for cap in capabilities:
                # Check capability-level access
                if not self._check_hierarchical_access(account, mcp_service, app=app, capability=cap):
                    continue

                # Use namespace: mcp_identifier_app_name:capability_name (sanitized for Google API)
                mcp_prefix = self._sanitize_tool_name(mcp_service.identifier) if mcp_service.identifier else "mcp"
                tool_name = f"{mcp_prefix}_{self._sanitized_app_name(app)}:{self._sanitize_tool_name(cap.name)}"

                tool = {
                    "name": tool_name,
                    "description": cap.description
                    or f"{cap.capability_type.upper()} tool: {cap.name} (from {app.name})",
                    "inputSchema": {"type": "object", "properties": {}, "required": []},
                }

                # Add body_params as input schema (preserve full schema including enums, descriptions, etc.)
                if cap.body_params:
                    try:
                        body_params = json.loads(cap.body_params)
                        # Use the complete schema from body_params if it has the right structure
                        if "properties" in body_params:
                            # Send full schema to LLM (including const-constrained fixed params)
                            # const制約により、LLMはパラメータを認識するが値は変更できない
                            tool["inputSchema"] = dict(body_params.items())
                        else:
                            # Fallback: treat as simple key-value params
                            for key, _value in body_params.items():
                                tool["inputSchema"]["properties"][key] = {
                                    "type": "string",
                                    "description": f"Parameter: {key}",
                                }
                    except json.JSONDecodeError:
                        pass

                # Add tool to list
                all_tools.append(tool)

        return {"jsonrpc": "2.0", "id": mcp_request.get("id"), "result": {"tools": all_tools}}

    def _handle_tool_call_for_mcp_service(self, account, mcp_service, mcp_request: dict[str, Any]) -> dict[str, Any]:
        """Execute tool call at MCP Service level with namespace support"""
        from app.models.models import Capability, Service

        params = mcp_request.get("params", {})
        tool_name = params.get("name")
        arguments = params.get("arguments", {})

        # Validate tool name
        if not tool_name:
            return {
                "jsonrpc": "2.0",
                "id": mcp_request.get("id"),
                "error": {"code": -32602, "message": "Missing tool name"},
            }

        app = None
        capability = None

        # Parse tool name: mcp_identifier_app_name:capability_name or simple capability_name
        if ":" in tool_name:
            # Namespaced format: mcp_prefix_app_name:capability_name
            prefix_and_app, sanitized_cap_name = tool_name.split(":", 1)

            # Extract mcp_prefix and app_name from prefix_and_app
            mcp_prefix = self._sanitize_tool_name(mcp_service.identifier) if mcp_service.identifier else "mcp"

            # Remove mcp_prefix from prefix_and_app to get sanitized_app_name
            if prefix_and_app.startswith(f"{mcp_prefix}_"):
                sanitized_app_name = prefix_and_app[len(mcp_prefix) + 1 :]  # +1 for underscore
            else:
                # Fallback: treat entire prefix as app name (for backward compatibility)
                sanitized_app_name = prefix_and_app

            # Find app by matching sanitized name (apply same fallback logic as tools/list)
            all_apps = self.db.session.query(Service).filter(Service.mcp_service_id == mcp_service.id).all()

            for a in all_apps:
                if self._sanitized_app_name(a) == sanitized_app_name:
                    app = a
                    # Find capability by matching sanitized name
                    all_caps = self.db.session.query(Capability).filter(Capability.app_id == app.id).all()
                    for c in all_caps:
                        if self._sanitize_tool_name(c.name) == sanitized_cap_name:
                            capability = c
                            break
                    break
        else:
            # Simple format: search across all apps
            apps = self.db.session.query(Service).filter(Service.mcp_service_id == mcp_service.id).all()

            for a in apps:
                cap = (
                    self.db.session.query(Capability)
                    .filter(Capability.app_id == a.id, Capability.name == tool_name)
                    .first()
                )
                if cap:
                    app = a
                    capability = cap
                    break

        if not capability or not app:
            return {
                "jsonrpc": "2.0",
                "id": mcp_request.get("id"),
                "error": {"code": -32602, "message": f"Tool not found: {tool_name}"},
            }

        # Check hierarchical permission
        if not self._check_hierarchical_access(account, mcp_service, app=app, capability=capability):
            return {
                "jsonrpc": "2.0",
                "id": mcp_request.get("id"),
                "error": {"code": -32000, "message": f"Permission denied for tool: {tool_name}"},
            }

        # Execute capability
        if capability.capability_type in ("api", "tool"):
            result = self._execute_api_call(app, capability, arguments)
        elif capability.capability_type in ("mcp", "mcp_tool"):
            result = self._execute_mcp_call(app, capability, arguments)
        else:
            return {
                "jsonrpc": "2.0",
                "id": mcp_request.get("id"),
                "error": {"code": -32603, "message": f"Unknown capability type: {capability.capability_type}"},
            }

        return {"jsonrpc": "2.0", "id": mcp_request.get("id"), "result": self._build_tool_call_result(result)}

    def _build_tool_call_result(self, result: dict[str, Any]) -> dict[str, Any]:
        """Convert an execution result into an MCP CallToolResult with isError set"""
        # Upstream MCP servers already answer with a CallToolResult, so relay it instead of re-wrapping
        if "jsonrpc" in result:
            if "error" in result:
                error = result["error"]
                message = error.get("message") if isinstance(error, dict) else str(error)
                return {"content": [{"type": "text", "text": message or "Upstream MCP error"}], "isError": True}
            upstream = result.get("result")
            if isinstance(upstream, dict) and "content" in upstream:
                return {**upstream, "isError": bool(upstream.get("isError", False))}

        return {
            "content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False, indent=2)}],
            "isError": not result.get("success", True),
        }

    def _handle_resources_list_for_mcp_service(
        self, account, mcp_service, mcp_request: dict[str, Any]
    ) -> dict[str, Any]:
        """Handle resources/list request - return resource-type capabilities from MCP service"""
        from app.models.models import Capability, Service

        # Check hierarchical access at MCP service level
        if not self._check_hierarchical_access(account, mcp_service):
            return {
                "jsonrpc": "2.0",
                "id": mcp_request.get("id"),
                "result": {
                    "resources": []  # Return empty if no access to MCP service
                },
            }

        # Get all apps under this MCP service
        apps = self.db.session.query(Service).filter(Service.mcp_service_id == mcp_service.id, Service.is_enabled).all()

        # Aggregate resource-type capabilities from all apps
        resource_list = []
        for app in apps:
            # Check app-level access
            if not self._check_hierarchical_access(account, mcp_service, app=app):
                continue

            # Get all resource-type capabilities for this app
            capabilities = (
                self.db.session.query(Capability)
                .filter(Capability.app_id == app.id, Capability.capability_type == "resource", Capability.is_enabled)
                .all()
            )

            for resource in capabilities:
                # Check capability-level access
                if not self._check_hierarchical_access(account, mcp_service, app=app, capability=resource):
                    continue

                # Get identifier from the MCP service
                identifier = mcp_service.identifier
                resource_item = {
                    "uri": resource.resource_uri or f"resource://{identifier}/{resource.name}",
                    "name": resource.name,
                    "description": resource.description or "",
                }
                if resource.resource_mime_type:
                    resource_item["mimeType"] = resource.resource_mime_type
                resource_list.append(resource_item)

        return {"jsonrpc": "2.0", "id": mcp_request.get("id"), "result": {"resources": resource_list}}

    def _accessible_capabilities(self, account, mcp_service, capability_type: str) -> list[tuple[Any, Any]]:
        """Return (app, capability) pairs of the given type that the account may use within mcp_service"""
        from app.models.models import Capability, Service

        if not self._check_hierarchical_access(account, mcp_service):
            return []

        pairs = []
        apps = self.db.session.query(Service).filter(Service.mcp_service_id == mcp_service.id).all()
        for app in apps:
            if not self._check_hierarchical_access(account, mcp_service, app=app):
                continue
            capabilities = (
                self.db.session.query(Capability)
                .filter(Capability.app_id == app.id, Capability.capability_type == capability_type)
                .all()
            )
            for cap in capabilities:
                if self._check_hierarchical_access(account, mcp_service, app=app, capability=cap):
                    pairs.append((app, cap))
        return pairs

    def _handle_resources_read(self, account, mcp_service, mcp_request: dict[str, Any]) -> dict[str, Any]:
        """Handle resources/read request - return content for capability resource"""
        params = mcp_request.get("params", {})
        uri = params.get("uri", "")

        if not uri:
            return {
                "jsonrpc": "2.0",
                "id": mcp_request.get("id"),
                "error": {"code": -32602, "message": "Missing required parameter: uri"},
            }

        # Inaccessible resources are reported as not found so their existence is not disclosed
        target_resource = None
        resource_uri = ""
        for _app, resource in self._accessible_capabilities(account, mcp_service, "resource"):
            stored_uri = resource.resource_uri or f"resource://{mcp_service.identifier}/{resource.name}"
            if stored_uri == uri or resource.name == uri:
                target_resource = resource
                resource_uri = stored_uri
                break

        if not target_resource:
            return {
                "jsonrpc": "2.0",
                "id": mcp_request.get("id"),
                "error": {"code": -32602, "message": f"Resource not found: {uri}"},
            }

        content = target_resource.template_content or ""
        mime_type = target_resource.resource_mime_type or "text/plain"

        return {
            "jsonrpc": "2.0",
            "id": mcp_request.get("id"),
            "result": {"contents": [{"uri": resource_uri, "mimeType": mime_type, "text": content}]},
        }

    def _handle_prompts_list(self, account, mcp_service, mcp_request: dict[str, Any]) -> dict[str, Any]:
        """Handle prompts/list request - return prompt-type capabilities the account may use"""
        prompt_list = []
        for _app, prompt in self._accessible_capabilities(account, mcp_service, "prompt"):
            prompt_item = {"name": prompt.name, "description": prompt.description or ""}

            # Extract arguments from body_params if exists
            if prompt.body_params:
                try:
                    body_params = (
                        json.loads(prompt.body_params) if isinstance(prompt.body_params, str) else prompt.body_params
                    )
                    if "properties" in body_params:
                        arguments = []
                        for arg_name, arg_spec in body_params["properties"].items():
                            argument = {
                                "name": arg_name,
                                "description": arg_spec.get("description", ""),
                                "required": arg_name in body_params.get("required", []),
                            }
                            arguments.append(argument)

                        if arguments:
                            prompt_item["arguments"] = arguments
                except (json.JSONDecodeError, TypeError, AttributeError):
                    logger.debug("Invalid body_params on prompt %s", prompt.id)

            prompt_list.append(prompt_item)

        return {"jsonrpc": "2.0", "id": mcp_request.get("id"), "result": {"prompts": prompt_list}}

    def _handle_prompts_get(self, account, mcp_service, mcp_request: dict[str, Any]) -> dict[str, Any]:
        """Handle prompts/get request - return specific prompt with filled template"""
        from app.models.models import Resource

        params = mcp_request.get("params", {})
        prompt_name = params.get("name")
        arguments = params.get("arguments", {})

        if not prompt_name:
            return {
                "jsonrpc": "2.0",
                "id": mcp_request.get("id"),
                "error": {"code": -32602, "message": "Missing prompt name"},
            }

        prompts = self._accessible_capabilities(account, mcp_service, "prompt")
        prompt = next((cap for _app, cap in prompts if cap.name == prompt_name), None)

        if not prompt:
            return {
                "jsonrpc": "2.0",
                "id": mcp_request.get("id"),
                "error": {"code": -32602, "message": f"Prompt not found: {prompt_name}"},
            }

        # Get template content from either template_content field or global Resource
        template = ""
        if prompt.template_content:
            template = prompt.template_content
        elif prompt.global_resource_id:
            # Get template from Resource table
            resource = (
                self.db.session.query(Resource)
                .filter(Resource.id == prompt.global_resource_id, Resource.is_enabled)
                .first()
            )
            if resource:
                template = resource.content or ""

        # Simple variable replacement: {{variable_name}}
        for key, value in arguments.items():
            template = template.replace(f"{{{{{key}}}}}", str(value))

        # Return formatted prompt
        return {
            "jsonrpc": "2.0",
            "id": mcp_request.get("id"),
            "result": {
                "description": prompt.description or "",
                "messages": [{"role": "user", "content": {"type": "text", "text": template}}],
            },
        }

    def _execute_api_call(self, service, capability, arguments: dict[str, Any]) -> dict[str, Any]:
        """Execute API call"""
        return call_capability_api(service, capability, arguments)

    def _parse_mcp_http_response(self, response) -> dict[str, Any]:
        """Parse an upstream MCP HTTP response.

        Supports both transports the MCP spec allows over HTTP:
        - a single ``application/json`` body (returned as-is), and
        - a ``text/event-stream`` (SSE) body, where the JSON-RPC payload is carried in
          ``data:`` lines. The last valid JSON ``data:`` event is returned.

        This lets Octopus MCP Proxy act as a Streamable HTTP client and relay through upstream
        servers (including another Octopus MCP Proxy) that answer with SSE.
        """
        content_type = response.headers.get("content-type", "") or response.headers.get("Content-Type", "")
        if "text/event-stream" in content_type:
            result = None
            for line in response.text.splitlines():
                stripped = line.strip()
                if stripped.startswith("data:"):
                    data = stripped[len("data:") :].strip()
                    if not data:
                        continue
                    try:
                        result = json.loads(data)
                    except json.JSONDecodeError:
                        continue
            if result is not None:
                return result
            return {"success": False, "error": "Empty or invalid SSE response from upstream MCP server"}
        # Plain JSON response
        return response.json()

    def _execute_mcp_call(self, service, capability, arguments: dict[str, Any]) -> dict[str, Any]:
        """Execute MCP relay call"""
        # For MCP relay, we need to connect to another MCP server

        try:
            # Parse MCP server URL
            # For mcp_tool type, use service.mcp_url (capability.service is the Service/App model)
            app = capability.service
            mcp_transport = getattr(app, "mcp_transport", "http") or "http"
            mcp_url = app.mcp_url if app else capability.url

            # Check if stdio transport
            if mcp_transport == "stdio":
                return self._execute_stdio_mcp_call(app, capability, arguments)

            if not mcp_url:
                return {"success": False, "error": "MCP server URL is not configured"}

            if mcp_url.startswith("http"):
                from app.services.variable_replacer import VariableReplacer

                # HTTP MCP connection (Streamable HTTP compatible client)
                headers = {}
                if service.common_headers:
                    headers.update(json.loads(service.common_headers))
                if capability.headers:
                    headers.update(json.loads(capability.headers))
                # Resolve {{VAR}} the same way connection tests and discovery do
                headers = VariableReplacer.replace_in_dict(headers)
                mcp_url = VariableReplacer.replace_in_string(mcp_url)

                # Advertise Streamable HTTP support to the upstream server: accept both a
                # single JSON response and an SSE (text/event-stream) response. This lets
                # Octopus MCP Proxy relay through upstream servers that only speak Streamable HTTP
                # (including another Octopus MCP Proxy), so a full streamable-http chain works.
                headers.setdefault("Accept", "application/json, text/event-stream")

                # Add depth header for daisy-chain loop prevention
                from flask import request

                current_depth = int(request.headers.get("X-AccelMCP-Depth", "0"))
                max_depth = 10  # Maximum daisy-chain depth

                if current_depth >= max_depth:
                    return {"success": False, "error": f"Maximum MCP daisy-chain depth ({max_depth}) exceeded"}

                headers["X-AccelMCP-Depth"] = str(current_depth + 1)

                # Get timeout from capability settings (used by both init and tools/call)
                timeout_seconds = float(capability.timeout_seconds or 30)

                # Check if we need to establish a session (GitHub Copilot MCP requires session)
                if "Mcp-Session-Id" not in headers:
                    # Send initialize request to establish session
                    init_request = {
                        "jsonrpc": "2.0",
                        "id": 0,
                        "method": "initialize",
                        "params": {
                            "protocolVersion": "2024-11-05",
                            "capabilities": {},
                            "clientInfo": {"name": "Octopus MCP Proxy", "version": "1.0.0"},
                        },
                    }

                    logger.debug("Initializing upstream MCP session")
                    init_response = httpx.post(mcp_url, headers=headers, json=init_request, timeout=timeout_seconds)
                    init_response.raise_for_status()

                    # Extract session ID from response headers (Streamable HTTP session)
                    session_id = init_response.headers.get("Mcp-Session-Id")
                    if session_id:
                        headers["Mcp-Session-Id"] = session_id
                        logger.debug("Upstream MCP session established")

                # Make MCP request
                mcp_request = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tools/call",
                    "params": {"name": capability.name, "arguments": arguments},
                }

                logger.debug("Sending MCP tools/call request to upstream server")

                response = httpx.post(mcp_url, headers=headers, json=mcp_request, timeout=timeout_seconds)

                logger.debug("Upstream MCP response status: %s", response.status_code)
                response.raise_for_status()

                # Upstream may answer with plain JSON or an SSE (Streamable HTTP) stream
                return self._parse_mcp_http_response(response)

            else:
                return {"success": False, "error": "Unsupported MCP transport"}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _execute_stdio_mcp_call(self, app, capability, arguments: dict[str, Any]) -> dict[str, Any]:
        """Execute stdio MCP relay call"""
        try:
            # Get stdio configuration from app
            command = app.stdio_command
            args = json.loads(app.stdio_args) if app.stdio_args else []
            env = json.loads(app.stdio_env) if app.stdio_env else {}
            cwd = app.stdio_cwd

            if not command:
                return {"success": False, "error": "stdio command is not configured"}

            # Replace variables in args and env
            from app.services.variable_replacer import VariableReplacer

            replacer = VariableReplacer()

            # Replace variables in args
            resolved_args = [replacer.replace_in_string(str(arg)) for arg in args]

            # Replace variables in env
            resolved_env = {}
            for key, value in env.items():
                resolved_env[key] = replacer.replace_in_string(str(value))

            # Bound the call so a hung server cannot hold the worker; cancellation also stops the process
            timeout_seconds = float(capability.timeout_seconds or 30)
            call = self._async_stdio_mcp_call(command, resolved_args, resolved_env, cwd, capability.name, arguments)
            try:
                return asyncio.run(asyncio.wait_for(call, timeout=timeout_seconds))
            except asyncio.TimeoutError:
                logger.error("stdio MCP call timed out after %ss", timeout_seconds)
                return {"success": False, "error": f"stdio MCP call timed out after {timeout_seconds:g}s"}

        except Exception as e:
            logger.error("stdio MCP call failed (%s)", type(e).__name__)
            return {"success": False, "error": str(e)}

    async def _async_stdio_mcp_call(
        self,
        command: str,
        args: list[str],
        env: dict[str, str],
        cwd: str | None,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        """Async implementation of stdio MCP call"""
        # Never pass the proxy's own environment (SECRET_KEY, DATABASE_URL, ...) to third-party servers
        server_params = StdioServerParameters(
            command=command, args=args, env={**get_default_environment(), **env}, cwd=cwd
        )

        try:
            async with stdio_client(server_params) as (read, write), ClientSession(read, write) as session:
                # Initialize the session
                await session.initialize()

                # Call the tool
                result = await session.call_tool(tool_name, arguments)

                # Convert result to dict format
                if result.content:
                    content_list = []
                    for item in result.content:
                        if hasattr(item, "text"):
                            content_list.append({"type": "text", "text": item.text})
                        elif hasattr(item, "data"):
                            content_list.append({"type": "blob", "data": item.data})
                        else:
                            content_list.append({"type": "unknown", "value": str(item)})

                    return {
                        "jsonrpc": "2.0",
                        "id": 1,
                        "result": {
                            "content": content_list,
                            "isError": result.isError if hasattr(result, "isError") else False,
                        },
                    }
                else:
                    return {"jsonrpc": "2.0", "id": 1, "result": {"content": [], "isError": False}}

        except Exception as e:
            logger.error("async stdio MCP call failed (%s)", type(e).__name__)
            return {"jsonrpc": "2.0", "id": 1, "error": {"code": -32603, "message": str(e)}}


def execute_capability_api(capability, params: dict[str, Any] | None = None):
    """
    Execute a capability API call for testing purposes

    Args:
        capability: Capability model instance
        params: Dictionary of parameters to pass to the API

    Returns:
        Dictionary with execution results including success status, data, and execution time
    """
    import time

    start_time = time.time()
    params = params or {}

    # Handle Resource type: simply return the stored content
    if capability.capability_type == "resource":
        end_time = time.time()
        execution_time_ms = int((end_time - start_time) * 1000)

        resource_content = capability.template_content or ""
        resource_uri = capability.resource_uri or ""
        resource_mime_type = capability.resource_mime_type or "text/plain"

        return {
            "success": True,
            "status_code": 200,
            "data": {"uri": resource_uri, "mimeType": resource_mime_type, "text": resource_content},
            "execution_time_ms": execution_time_ms,
        }

    result = call_capability_api(capability.service, capability, params)
    result["execution_time_ms"] = int((time.time() - start_time) * 1000)
    return result


def _build_api_request_body(capability, arguments: dict[str, Any]) -> dict[str, Any]:
    """Merge const (fixed) params from body_params with caller-provided arguments.

    Const values always win; arguments for unknown keys are passed through. If body_params
    cannot be parsed, the arguments are sent as-is rather than being dropped.
    """
    from app.services.variable_replacer import VariableReplacer

    if not capability.body_params:
        return dict(arguments)

    try:
        parsed = (
            json.loads(capability.body_params) if isinstance(capability.body_params, str) else capability.body_params
        )
    except (json.JSONDecodeError, TypeError):
        logger.warning("Invalid body_params on capability %s; sending arguments as-is", capability.id)
        return dict(arguments)
    if not isinstance(parsed, dict):
        return dict(arguments)

    if "properties" not in parsed:
        # Old format: simple key-value pairs are fixed params
        return {**VariableReplacer.replace_in_dict(parsed), **arguments}

    body: dict[str, Any] = {}
    properties = parsed.get("properties", {})
    for key, prop_def in properties.items():
        if isinstance(prop_def, dict) and "const" in prop_def:
            const_value = prop_def["const"]
            body[key] = VariableReplacer.replace_in_string(const_value) if isinstance(const_value, str) else const_value
    for key, value in arguments.items():
        prop_def = properties.get(key)
        if not (isinstance(prop_def, dict) and "const" in prop_def):
            body[key] = value
    return body


def call_capability_api(service, capability, arguments: dict[str, Any]) -> dict[str, Any]:
    """Send the HTTP request for an API (tool) capability. Shared by tools/call and the admin test run."""
    from app.services.variable_replacer import VariableReplacer

    # Merge headers: service common headers + capability specific headers
    headers = {}
    if service.common_headers:
        headers.update(json.loads(service.common_headers))
    if capability.headers:
        headers.update(json.loads(capability.headers))
    headers = VariableReplacer.replace_in_dict(headers)
    url = VariableReplacer.replace_in_string(capability.url)
    body = _build_api_request_body(capability, arguments)

    http_method = headers.get("X-HTTP-Method", "POST").upper()
    timeout_seconds = float(capability.timeout_seconds or 30)
    # Error details reach MCP clients, so they show the configured URL, never the one with resolved secrets
    display_url = capability.url

    try:
        if http_method == "GET":
            # For GET, use query parameters instead of body
            response = httpx.get(url, params=body, headers=headers, timeout=timeout_seconds)
        else:
            response = httpx.post(url, headers=headers, json=body, timeout=timeout_seconds)

        response.raise_for_status()

        return {
            "success": True,
            "status_code": response.status_code,
            "data": response.json()
            if response.headers.get("content-type", "").startswith("application/json")
            else response.text,
        }
    except httpx.TimeoutException:
        return {
            "success": False,
            "error": {
                "code": "API_TIMEOUT",
                "message": f"APIリクエストがタイムアウトしました（{timeout_seconds}秒）",
                "details": {
                    "url": display_url,
                    "timeout": timeout_seconds,
                    "suggestion": "Capability設定でtimeout_secondsを増やすか、API側の負荷を確認してください",
                },
            },
        }
    except httpx.HTTPStatusError as e:
        return {
            "success": False,
            "error": {
                "code": f"HTTP_{e.response.status_code}",
                "message": f"HTTPエラー: {e.response.status_code} {e.response.reason_phrase}",
                "details": {
                    "url": display_url,
                    "status_code": e.response.status_code,
                    "response_body": e.response.text[:500] if e.response.text else None,
                },
            },
        }
    except httpx.HTTPError as e:
        return {
            "success": False,
            "error": {
                "code": "HTTP_ERROR",
                "message": f"HTTP通信エラー: {str(e)}",
                "details": {"url": display_url, "error_type": type(e).__name__},
            },
        }
