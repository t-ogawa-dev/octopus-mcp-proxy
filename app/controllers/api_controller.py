"""
API Controller
Handles RESTful API endpoints for services, capabilities, accounts, and permissions
"""

import csv
import io
import json
import secrets
from datetime import datetime, timedelta, timezone

import yaml
from flask import Blueprint, Response, jsonify, request, session
from werkzeug.exceptions import NotFound

from app.controllers.auth_controller import login_required
from app.models.models import (
    AccountPermission,
    AdminCredentials,
    AdminSettings,
    Capability,
    ConnectionAccount,
    McpCapabilityTemplate,
    McpConnectionLog,
    McpService,
    McpServiceTemplate,
    Resource,
    ResourceAccountAccess,
    Service,
    Variable,
    db,
    get_or_404,
)
from app.services.app_service import create_app_record, update_app_record
from app.services.audit_logger import audit_log
from app.services.connection_test import check_http_connection, check_stdio_connection

# Service is now mapped to 'apps' table, but keep the class name for compatibility

api_bp = Blueprint("api", __name__)


# Error handlers for API blueprint - return JSON instead of HTML
@api_bp.errorhandler(NotFound)
def handle_not_found(e):
    """Handle 404 errors with JSON response instead of HTML"""
    return jsonify({"error": str(e.description or "Resource not found")}), 404


@api_bp.errorhandler(500)
def handle_internal_error(e):
    """Handle 500 errors with JSON response instead of HTML"""
    return jsonify({"error": "Internal server error", "message": str(e)}), 500


# ============= MCP Service API =============


@api_bp.route("/mcp-services", methods=["GET", "POST"])
@login_required
@audit_log("mcp_service", action_type="create")
def mcp_services():
    """Get all MCP services or create new MCP service"""
    if request.method == "GET":
        services = McpService.query.all()
        return jsonify([s.to_dict() for s in services])

    elif request.method == "POST":
        data = request.get_json()

        # Check for duplicate identifier
        if McpService.query.filter_by(identifier=data["identifier"]).first():
            return jsonify({"error": "同じidentifierのMCPサービスが既に存在します"}), 409

        mcp_service = McpService(
            name=data["name"],
            identifier=data["identifier"],
            routing_type=data.get("routing_type", "subdomain"),
            description=data.get("description", ""),
        )
        db.session.add(mcp_service)
        db.session.commit()
        return jsonify(mcp_service.to_dict()), 201


@api_bp.route("/mcp-services/<int:mcp_service_id>", methods=["GET", "PUT", "DELETE"])
@login_required
@audit_log("mcp_service")
def mcp_service_detail(mcp_service_id):
    """Get, update, or delete a specific MCP service"""
    mcp_service = get_or_404(McpService, mcp_service_id)

    if request.method == "GET":
        result = mcp_service.to_dict()
        # Include apps list
        result["apps"] = [app.to_dict() for app in mcp_service.apps]
        return jsonify(result)

    elif request.method == "PUT":
        data = request.get_json()
        mcp_service.name = data.get("name", mcp_service.name)
        mcp_service.identifier = data.get("identifier", mcp_service.identifier)
        mcp_service.routing_type = data.get("routing_type", mcp_service.routing_type)
        mcp_service.description = data.get("description", mcp_service.description)
        db.session.commit()
        return jsonify(mcp_service.to_dict())

    elif request.method == "DELETE":
        db.session.delete(mcp_service)
        db.session.commit()
        return "", 204


@api_bp.route("/mcp-services/<int:mcp_service_id>/toggle", methods=["POST"])
@login_required
@audit_log("mcp_service", action_type="update")
def toggle_mcp_service(mcp_service_id):
    """Toggle MCP service enabled/disabled status"""
    mcp_service = get_or_404(McpService, mcp_service_id)
    mcp_service.is_enabled = not mcp_service.is_enabled
    db.session.commit()
    return jsonify(mcp_service.to_dict())


@api_bp.route("/mcp-services/<int:mcp_service_id>/export", methods=["GET"])
@login_required
def export_mcp_service(mcp_service_id):
    """Export MCP service with all apps and capabilities as YAML"""
    mcp_service = get_or_404(McpService, mcp_service_id)

    # Build nested structure: service -> apps -> capabilities
    export_data = {
        "name": mcp_service.name,
        "identifier": mcp_service.identifier,
        "description": mcp_service.description,
        "apps": [],
    }

    # Include all apps under this service
    for app in mcp_service.apps:
        app_data = {
            "name": app.name,
            "description": app.description,
            "service_type": app.service_type,
            "mcp_url": app.mcp_url,
            "common_headers": json.loads(app.common_headers) if app.common_headers else {},
            "capabilities": [],
        }

        # Include all capabilities under this app
        for capability in app.capabilities:
            cap_data = {
                "name": capability.name,
                "capability_type": capability.capability_type,
                "description": capability.description,
                "url": capability.url,
                "headers": json.loads(capability.headers) if capability.headers else {},
                "body_params": json.loads(capability.body_params) if capability.body_params else {},
                "template_content": capability.template_content,
            }
            app_data["capabilities"].append(cap_data)

        export_data["apps"].append(app_data)

    # Convert to YAML
    yaml_content = yaml.dump(export_data, allow_unicode=True, default_flow_style=False, sort_keys=False)
    return Response(
        yaml_content,
        mimetype="application/x-yaml",
        headers={"Content-Disposition": f'attachment; filename="{mcp_service.name}.yaml"'},
    )


@api_bp.route("/mcp-services/import", methods=["POST"])
@login_required
def import_mcp_service():
    """Import MCP service from exported YAML"""
    import random
    import string

    # Parse YAML from request body
    try:
        data = yaml.safe_load(request.data)
    except yaml.YAMLError as e:
        return jsonify({"error": f"Invalid YAML format: {str(e)}"}), 400

    # Validate required fields
    if not data.get("name") or not data.get("identifier"):
        return jsonify({"error": "Missing required fields: name, identifier"}), 400

    # Check for identifier collision
    original_identifier = data["identifier"]
    identifier = original_identifier

    # If identifier exists, append random 5 characters
    while McpService.query.filter_by(identifier=identifier).first():
        random_suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=5))
        identifier = f"{original_identifier}-{random_suffix}"

    # Create MCP service
    mcp_service = McpService(name=data["name"], identifier=identifier, description=data.get("description", ""))
    db.session.add(mcp_service)
    db.session.flush()  # Get ID without committing

    # Import apps
    for app_data in data.get("apps", []):
        app = Service(
            mcp_service_id=mcp_service.id,
            name=app_data["name"],
            description=app_data.get("description", ""),
            service_type=app_data.get("service_type", "api"),
            mcp_url=app_data.get("mcp_url"),
            common_headers=json.dumps(app_data.get("common_headers", {})),
        )
        db.session.add(app)
        db.session.flush()  # Get ID without committing

        # Import capabilities
        for cap_data in app_data.get("capabilities", []):
            capability = Capability(
                app_id=app.id,
                name=cap_data["name"],
                capability_type=cap_data.get("capability_type", "resource"),
                description=cap_data.get("description", ""),
                url=cap_data.get("url", ""),
                headers=json.dumps(cap_data.get("headers", {})),
                body_params=json.dumps(cap_data.get("body_params", {})),
                template_content=cap_data.get("template_content"),
            )
            db.session.add(capability)

    db.session.commit()

    return jsonify(
        {"success": True, "mcp_service": mcp_service.to_dict(), "identifier_changed": identifier != original_identifier}
    ), 201


# ============= App API =============


@api_bp.route("/apps/test-connection", methods=["POST"])
@login_required
def test_service_connection():
    """Test MCP server connection"""
    data = request.get_json() or {}
    mcp_url = data.get("mcp_url")
    if not mcp_url:
        return jsonify({"success": False, "error": "MCP URL is required"}), 400

    body, status = check_http_connection(mcp_url, data.get("common_headers") or {})
    return jsonify(body), status


@api_bp.route("/apps/test-stdio-connection", methods=["POST"])
@login_required
def test_stdio_connection():
    """Test stdio MCP server connection"""
    data = request.get_json() or {}
    command = data.get("command")
    if not command:
        return jsonify({"success": False, "error": "Command is required"}), 400

    body, status = check_stdio_connection(command, data.get("args") or [], data.get("env") or {}, data.get("cwd"))
    return jsonify(body), status


@api_bp.route("/mcp-services/<int:mcp_service_id>/apps", methods=["GET", "POST"])
@login_required
@audit_log("app", action_type="create")
def mcp_service_apps(mcp_service_id):
    """Get all apps for an MCP service or create new app under MCP service"""
    mcp_service = get_or_404(McpService, mcp_service_id)

    if request.method == "GET":
        return jsonify([app.to_dict() for app in mcp_service.apps])

    elif request.method == "POST":
        service = create_app_record(request.get_json(), mcp_service_id)
        return jsonify(service.to_dict()), 201


@api_bp.route("/apps", methods=["GET", "POST"])
@login_required
@audit_log("app", action_type="create")
def apps():
    """Get all apps or create new app (legacy endpoint)"""
    if request.method == "GET":
        services = Service.query.all()
        return jsonify([s.to_dict() for s in services])

    elif request.method == "POST":
        # If mcp_service_id is omitted, create standalone (for backward compatibility)
        data = request.get_json()
        service = create_app_record(data, data.get("mcp_service_id"))
        return jsonify(service.to_dict()), 201


@api_bp.route("/apps/<int:service_id>", methods=["GET", "PUT", "DELETE"])
@login_required
@audit_log("app")
def app_detail(service_id):
    """Get, update, or delete a specific app"""
    service = get_or_404(Service, service_id)

    if request.method == "GET":
        return jsonify(service.to_dict())

    elif request.method == "PUT":
        update_app_record(service, request.get_json())
        return jsonify(service.to_dict())

    elif request.method == "DELETE":
        db.session.delete(service)
        db.session.commit()
        return "", 204


@api_bp.route("/apps/<int:service_id>/toggle", methods=["POST"])
@login_required
@audit_log("app", action_type="update")
def toggle_app(service_id):
    """Toggle app enabled/disabled status"""
    service = get_or_404(Service, service_id)
    service.is_enabled = not service.is_enabled
    db.session.commit()
    return jsonify(service.to_dict())


# ============= Capability API =============


@api_bp.route("/apps/<int:service_id>/capabilities", methods=["GET", "POST"])
@login_required
def capabilities(service_id):
    """Get all capabilities for a service or create new capability"""
    get_or_404(Service, service_id)

    if request.method == "GET":
        capabilities = Capability.query.filter_by(app_id=service_id).all()
        return jsonify([c.to_dict() for c in capabilities])

    elif request.method == "POST":
        data = request.get_json()

        # 同じアプリ内に同じ名前のCapabilityが存在しないかチェック
        existing = Capability.query.filter_by(app_id=service_id, name=data["name"]).first()
        if existing:
            return jsonify({"error": "同じ名前のCapabilityが既に存在します"}), 409

        # Handle global resource ID or create new Resource record
        global_resource_id = data.get("global_resource_id")
        resource_uri = data.get("resource_uri")
        resource_mime_type = data.get("resource_mime_type")
        template_content = data.get("template_content")
        resource_name = data.get("resource_name")  # New field for resource name
        capability_type = data["capability_type"]

        # Only create Resource record for 'resource' type (not for 'prompt' type)
        if capability_type == "resource" and not global_resource_id and (resource_uri or template_content):
            # Create new Resource record with auto-generated resource_id
            new_resource = Resource(
                resource_id=Resource.generate_resource_id(),
                name=resource_name or data["name"],  # Use provided resource name or fall back to capability name
                mime_type=resource_mime_type or "text/plain",
                content=template_content or "",
                description=data.get("description", ""),
                access_control="public",  # Resources have public access by default
                is_enabled=True,
            )
            db.session.add(new_resource)
            db.session.flush()  # Get the resource ID

            # Use the new resource ID
            global_resource_id = new_resource.id
            # Clear inline fields since we're using global resource
            resource_uri = None
            resource_mime_type = None
            template_content = None

        capability = Capability(
            app_id=service_id,
            name=data["name"],
            capability_type=data["capability_type"],  # 'tool', 'resource', 'prompt', 'mcp_tool'
            url=data.get("url"),
            headers=json.dumps(data.get("headers", {})),
            body_params=json.dumps(data.get("body_params", {})),
            template_content=template_content,
            resource_uri=resource_uri,
            resource_mime_type=resource_mime_type,
            global_resource_id=global_resource_id,
            description=data.get("description", ""),
            timeout_seconds=data.get("timeout_seconds", 30),
        )
        db.session.add(capability)
        db.session.flush()  # IDを取得するためにflush

        # 権限設定
        if "account_ids" in data:
            for account_id in data["account_ids"]:
                permission = AccountPermission(capability_id=capability.id, account_id=account_id)
                db.session.add(permission)

        db.session.commit()
        return jsonify(capability.to_dict()), 201


@api_bp.route("/capabilities/<int:capability_id>", methods=["GET", "PUT", "DELETE"])
@login_required
@audit_log("capability")
def capability_detail(capability_id):
    """Get, update, or delete a specific capability"""
    capability = get_or_404(Capability, capability_id)

    if request.method == "GET":
        return jsonify(capability.to_dict())

    elif request.method == "PUT":
        data = request.get_json()

        # 名前を変更する場合、同じアプリ内に同じ名前のCapabilityが存在しないかチェック
        new_name = data.get("name", capability.name)
        if new_name != capability.name:
            existing = (
                Capability.query.filter_by(app_id=capability.app_id, name=new_name)
                .filter(Capability.id != capability.id)
                .first()
            )
            if existing:
                return jsonify({"error": "同じ名前のCapabilityが既に存在します"}), 409

        # Handle resource updates
        global_resource_id = data.get("global_resource_id", capability.global_resource_id)
        resource_uri = data.get("resource_uri", capability.resource_uri)
        resource_mime_type = data.get("resource_mime_type", capability.resource_mime_type)
        template_content = data.get("template_content", capability.template_content)
        resource_name = data.get("resource_name")  # New field for resource name
        new_capability_type = data.get("capability_type", capability.capability_type)

        # Only create Resource record for 'resource' type (not for 'prompt' type)
        if new_capability_type == "resource" and not global_resource_id and (resource_uri or template_content):
            # Create new Resource record with auto-generated resource_id
            new_resource = Resource(
                resource_id=Resource.generate_resource_id(),
                name=resource_name or new_name,  # Use provided resource name or fall back to capability name
                mime_type=resource_mime_type or "text/plain",
                content=template_content or "",
                description=data.get("description", capability.description),
                access_control="public",
                is_enabled=True,
            )
            db.session.add(new_resource)
            db.session.flush()

            global_resource_id = new_resource.id
            resource_uri = None
            resource_mime_type = None
            template_content = None

        capability.name = new_name
        capability.capability_type = data.get("capability_type", capability.capability_type)
        capability.url = data.get("url", capability.url)
        capability.headers = json.dumps(data.get("headers", {}))
        capability.body_params = json.dumps(data.get("body_params", {}))
        capability.template_content = template_content
        capability.resource_uri = resource_uri
        capability.resource_mime_type = resource_mime_type
        capability.global_resource_id = global_resource_id
        capability.description = data.get("description", capability.description)
        capability.timeout_seconds = data.get("timeout_seconds", capability.timeout_seconds)

        # 権限設定を更新
        if "account_ids" in data:
            # 既存の権限を削除
            AccountPermission.query.filter_by(capability_id=capability.id).delete()
            # 新しい権限を追加
            for account_id in data["account_ids"]:
                permission = AccountPermission(capability_id=capability.id, account_id=account_id)
                db.session.add(permission)

        db.session.commit()
        return jsonify(capability.to_dict())

    elif request.method == "DELETE":
        db.session.delete(capability)
        db.session.commit()
        return "", 204


@api_bp.route("/capabilities/<int:capability_id>/toggle", methods=["POST"])
@login_required
@audit_log("capability", action_type="update")
def toggle_capability(capability_id):
    """Toggle capability enabled/disabled status"""
    capability = get_or_404(Capability, capability_id)
    capability.is_enabled = not capability.is_enabled
    db.session.commit()
    return jsonify(capability.to_dict())


@api_bp.route("/capabilities/<int:capability_id>/test", methods=["POST"])
@login_required
def test_capability(capability_id):
    """Test capability execution with provided parameters"""
    capability = get_or_404(Capability, capability_id)
    data = request.get_json() or {}

    # Import here to avoid circular imports
    from app.services.mcp_handler import execute_capability_api

    # Get test parameters from request
    test_params = data.get("params", {})

    # Execute the capability
    try:
        result = execute_capability_api(capability, test_params)

        # Return detailed response
        if result.get("success"):
            return jsonify(
                {
                    "success": True,
                    "status_code": result.get("status_code"),
                    "data": result.get("data"),
                    "execution_time_ms": result.get("execution_time_ms", 0),
                }
            )
        else:
            return jsonify({"success": False, "error": result.get("error", "Unknown error")}), 500
    except Exception as e:
        return jsonify(
            {
                "success": False,
                "error": {
                    "code": "EXECUTION_ERROR",
                    "message": str(e),
                    "details": {"capability_id": capability_id, "capability_name": capability.name},
                },
            }
        ), 500


# ============= Connection Account API =============


@api_bp.route("/accounts", methods=["GET", "POST"])
@login_required
@audit_log("account", action_type="create", get_resource_name=lambda d: d.get("name"))
def accounts():
    """Get all connection accounts or create new account"""
    if request.method == "GET":
        accounts = ConnectionAccount.query.all()
        return jsonify([a.to_dict() for a in accounts])

    elif request.method == "POST":
        data = request.get_json()

        account = ConnectionAccount(
            name=data["name"], bearer_token=secrets.token_urlsafe(32), notes=data.get("notes", "")
        )
        db.session.add(account)
        db.session.commit()
        return jsonify(account.to_dict()), 201


@api_bp.route("/accounts/<int:account_id>", methods=["GET", "PUT", "DELETE"])
@login_required
@audit_log("account", get_resource_name=lambda d: d.get("name"))
def account_detail(account_id):
    """Get, update, or delete a specific connection account"""
    account = get_or_404(ConnectionAccount, account_id)

    if request.method == "GET":
        return jsonify(account.to_dict())

    elif request.method == "PUT":
        data = request.get_json()
        if account.is_system:
            # System accounts: only allow notes update (name is fixed)
            account.notes = data.get("notes", account.notes)
        else:
            account.name = data.get("name", account.name)
            account.notes = data.get("notes", account.notes)

        db.session.commit()
        return jsonify(account.to_dict())

    elif request.method == "DELETE":
        if account.is_system:
            return jsonify({"error": "システムアカウントは削除できません"}), 403
        db.session.delete(account)
        db.session.commit()
        return "", 204


@api_bp.route("/accounts/<int:account_id>/regenerate_token", methods=["POST"])
@login_required
def regenerate_token(account_id):
    """Regenerate account's bearer token"""
    account = get_or_404(ConnectionAccount, account_id)
    account.bearer_token = secrets.token_urlsafe(32)
    db.session.commit()
    return jsonify(account.to_dict())


# ============= Permission API =============


@api_bp.route("/accounts/<int:account_id>/permissions", methods=["GET", "POST"])
@login_required
def account_permissions(account_id):
    """Get account permissions or add new permission (supports 3-tier)"""
    get_or_404(ConnectionAccount, account_id)

    if request.method == "GET":
        permissions = AccountPermission.query.filter_by(account_id=account_id).all()
        return jsonify([p.to_dict() for p in permissions])

    elif request.method == "POST":
        data = request.get_json()

        # Determine which level of permission to add
        mcp_service_id = data.get("mcp_service_id")
        app_id = data.get("app_id")
        capability_id = data.get("capability_id")

        # Validate: exactly one must be provided
        provided = sum([bool(mcp_service_id), bool(app_id), bool(capability_id)])
        if provided != 1:
            return jsonify({"error": "Exactly one of mcp_service_id, app_id, or capability_id must be provided"}), 400

        # Check if permission already exists
        existing = AccountPermission.query.filter_by(
            account_id=account_id, mcp_service_id=mcp_service_id, app_id=app_id, capability_id=capability_id
        ).first()

        if existing:
            return jsonify({"error": "この権限は既に付与されています"}), 400

        # Verify the resource exists
        if mcp_service_id:
            get_or_404(McpService, mcp_service_id)
        elif app_id:
            get_or_404(Service, app_id)
        elif capability_id:
            get_or_404(Capability, capability_id)

        permission = AccountPermission(
            account_id=account_id, mcp_service_id=mcp_service_id, app_id=app_id, capability_id=capability_id
        )
        db.session.add(permission)
        db.session.commit()
        return jsonify(permission.to_dict()), 201


@api_bp.route("/permissions/<int:permission_id>", methods=["DELETE"])
@login_required
def permission_delete(permission_id):
    """Delete a permission"""
    permission = get_or_404(AccountPermission, permission_id)
    db.session.delete(permission)
    db.session.commit()
    return "", 204


@api_bp.route("/capabilities/<int:capability_id>/permissions", methods=["GET", "PUT"])
@login_required
def capability_permissions(capability_id):
    """Get or update permissions for a capability"""
    get_or_404(Capability, capability_id)

    if request.method == "GET":
        # Get all accounts with permissions for this capability
        permissions = AccountPermission.query.filter_by(capability_id=capability_id).all()
        enabled_account_ids = [p.account_id for p in permissions]

        # Get enabled accounts (with permission)
        enabled_accounts = ConnectionAccount.query.filter(ConnectionAccount.id.in_(enabled_account_ids)).all()

        # Get disabled accounts (without permission)
        disabled_accounts = ConnectionAccount.query.filter(~ConnectionAccount.id.in_(enabled_account_ids)).all()

        return jsonify(
            {"enabled": [a.to_dict() for a in enabled_accounts], "disabled": [a.to_dict() for a in disabled_accounts]}
        )

    elif request.method == "PUT":
        data = request.get_json()
        account_ids = data.get("account_ids", [])

        # Delete all existing permissions for this capability (use 'fetch' to sync session)
        AccountPermission.query.filter_by(capability_id=capability_id).delete(synchronize_session="fetch")

        # Add new permissions
        for account_id in account_ids:
            # Verify account exists
            account = ConnectionAccount.query.filter_by(id=account_id).first()
            if account:
                permission = AccountPermission(account_id=account_id, capability_id=capability_id)
                db.session.add(permission)

        db.session.commit()
        return jsonify({"message": "権限設定を更新しました"}), 200


# ============= Settings API =============


@api_bp.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    """Get all settings or create/update a setting"""
    if request.method == "GET":
        all_settings = AdminSettings.query.all()
        return jsonify([s.to_dict() for s in all_settings])

    elif request.method == "POST":
        data = request.get_json()
        setting_key = data.get("setting_key")
        setting_value = data.get("setting_value")

        if not setting_key:
            return jsonify({"error": "setting_key is required"}), 400

        # Update or create
        setting = AdminSettings.query.filter_by(setting_key=setting_key).first()
        if setting:
            setting.setting_value = setting_value
            db.session.commit()
            return jsonify(setting.to_dict()), 200
        else:
            setting = AdminSettings(setting_key=setting_key, setting_value=setting_value)
            db.session.add(setting)
            db.session.commit()
            return jsonify(setting.to_dict()), 201


@api_bp.route("/settings/<string:setting_key>", methods=["GET", "DELETE"])
@login_required
def setting_detail(setting_key):
    """Get or delete a specific setting"""
    setting = AdminSettings.query.filter_by(setting_key=setting_key).first()

    if request.method == "GET":
        if not setting:
            return jsonify({"error": "Setting not found"}), 404
        return jsonify(setting.to_dict())

    elif request.method == "DELETE":
        if not setting:
            return jsonify({"error": "Setting not found"}), 404
        db.session.delete(setting)
        db.session.commit()
        return "", 204


@api_bp.route("/settings/language", methods=["GET", "POST"])
@login_required
def language_setting():
    """Get or set language preference"""
    if request.method == "GET":
        setting = AdminSettings.query.filter_by(setting_key="language").first()
        if setting:
            language = setting.setting_value
            is_initialized = True
        else:
            language = None
            is_initialized = False
        return jsonify({"language": language, "is_initialized": is_initialized})

    elif request.method == "POST":
        data = request.get_json()
        language = data.get("language", "ja")

        # Validate language
        if language not in ["ja", "en"]:
            return jsonify({"error": "Invalid language"}), 400

        # Update or create setting
        setting = AdminSettings.query.filter_by(setting_key="language").first()
        if setting:
            setting.setting_value = language
        else:
            setting = AdminSettings(setting_key="language", setting_value=language)
            db.session.add(setting)

        db.session.commit()
        return jsonify({"message": "Language setting updated", "language": language}), 200


# ============= Template API =============


@api_bp.route("/mcp-templates", methods=["GET"])
@login_required
def templates():
    """Get all service templates"""
    from app.models.models import McpServiceTemplate

    template_type = request.args.get("type")  # 'builtin' or 'custom'
    category = request.args.get("category")

    query = McpServiceTemplate.query
    if template_type:
        query = query.filter_by(template_type=template_type)
    if category:
        query = query.filter_by(category=category)

    templates = query.all()
    return jsonify([t.to_dict() for t in templates])


@api_bp.route("/mcp-templates/<int:template_id>", methods=["GET", "PUT", "DELETE"])
@login_required
def template_detail(template_id):
    """Get, update, or delete a specific template"""

    template = get_or_404(McpServiceTemplate, template_id)

    if request.method == "GET":
        result = template.to_dict()
        # For API templates, include capabilities
        if template.service_type == "api":
            result["capabilities"] = [cap.to_dict() for cap in template.capability_templates]
        return jsonify(result)

    elif request.method == "PUT":
        # Only custom templates can be updated
        if template.template_type != "custom":
            return jsonify({"error": "Cannot modify builtin templates"}), 403

        data = request.get_json()
        template.name = data.get("name", template.name)
        template.service_type = data.get("service_type", template.service_type)
        template.mcp_url = data.get("mcp_url", template.mcp_url)
        template.official_url = data.get("official_url", template.official_url)
        template.description = data.get("description", template.description)
        if "common_headers" in data:
            template.common_headers = json.dumps(data["common_headers"] or {})
        template.icon = data.get("icon", template.icon)
        template.category = data.get("category", template.category)
        db.session.commit()
        return jsonify(template.to_dict())

    elif request.method == "DELETE":
        # Only custom templates can be deleted
        if template.template_type != "custom":
            return jsonify({"error": "Cannot delete builtin templates"}), 403

        db.session.delete(template)
        db.session.commit()
        return "", 204


@api_bp.route("/mcp-templates", methods=["POST"])
@login_required
def create_template():
    """Create a new custom template"""
    from app.models.models import McpServiceTemplate

    data = request.get_json()

    template = McpServiceTemplate(
        name=data["name"],
        template_type="custom",
        service_type=data.get("service_type", "mcp"),
        mcp_url=data.get("mcp_url", ""),
        official_url=data.get("official_url", ""),
        description=data.get("description", ""),
        common_headers=json.dumps(data.get("common_headers", {})),
        icon=data.get("icon", "📦"),
        category=data.get("category", "Custom"),
    )
    db.session.add(template)
    db.session.commit()
    return jsonify(template.to_dict()), 201


@api_bp.route("/mcp-templates/<int:template_id>/export", methods=["GET"])
@login_required
def export_template(template_id):
    """Export template as YAML"""
    from app.models.models import McpServiceTemplate

    template = get_or_404(McpServiceTemplate, template_id)
    export_data = template.to_export_dict()

    # Convert to YAML
    yaml_content = yaml.dump(export_data, allow_unicode=True, default_flow_style=False, sort_keys=False)
    return Response(
        yaml_content,
        mimetype="application/x-yaml",
        headers={"Content-Disposition": f'attachment; filename="template-{template.name}.yaml"'},
    )


@api_bp.route("/mcp-templates/import", methods=["POST"])
@login_required
def import_template():
    """Import template from YAML"""
    from app.models.models import McpServiceTemplate

    # Parse YAML from request body
    try:
        data = yaml.safe_load(request.data)
    except yaml.YAMLError as e:
        return jsonify({"error": f"Invalid YAML format: {str(e)}"}), 400

    # Create template as custom
    template = McpServiceTemplate(
        name=data["name"],
        template_type="custom",
        service_type=data.get("service_type", "mcp"),
        mcp_url=data.get("mcp_url", ""),
        official_url=data.get("official_url", ""),
        description=data.get("description", ""),
        common_headers=json.dumps(data.get("common_headers", {})),
        icon=data.get("icon", "📦"),
        category=data.get("category", "Custom"),
    )
    db.session.add(template)
    db.session.commit()
    return jsonify(template.to_dict()), 201


@api_bp.route("/mcp-templates/<int:template_id>/prepare-app", methods=["POST"])
@login_required
def prepare_app_from_template(template_id):
    """Prepare app creation from template - returns URL to app creation form with pre-filled data"""

    template = get_or_404(McpServiceTemplate, template_id)
    data = request.get_json()

    mcp_service_id = data.get("mcp_service_id")
    if not mcp_service_id:
        return jsonify({"error": "MCP service ID is required"}), 400

    # Check if MCP service exists
    get_or_404(McpService, mcp_service_id)

    template_data = {
        "name": template.name,
        "service_type": template.service_type,
        "mcp_url": template.mcp_url or "",
        "description": template.description or "",
        "common_headers": json.loads(template.common_headers) if template.common_headers else {},
        "official_url": template.official_url or "",
    }

    # For API templates, include capabilities
    if template.service_type == "api":
        template_data["capabilities"] = [cap.to_dict() for cap in template.capability_templates]

    # Return URL to app creation form with template data as query parameters
    return jsonify({"redirect_url": f"/mcp-services/{mcp_service_id}/apps/new", "template_data": template_data}), 200


# ============= Template Capability API =============


@api_bp.route("/mcp-templates/<int:template_id>/capabilities", methods=["GET", "POST"])
@login_required
def template_capabilities(template_id):
    """Get all capabilities for a template or create new capability"""
    template = get_or_404(McpServiceTemplate, template_id)

    # Only API templates have capabilities
    if template.service_type != "api":
        return jsonify({"error": "Only API templates can have capabilities"}), 400

    if request.method == "GET":
        capabilities = McpCapabilityTemplate.query.filter_by(template_id=template_id).all()
        return jsonify([cap.to_dict() for cap in capabilities])

    elif request.method == "POST":
        # Only custom templates can be modified
        if template.template_type != "custom":
            return jsonify({"error": "Cannot modify builtin templates"}), 403

        data = request.get_json()
        capability = McpCapabilityTemplate(
            template_id=template_id,
            name=data["name"],
            capability_type=data.get("capability_type", "tool"),
            endpoint_path=data.get("endpoint_path", ""),
            method=data.get("method", "GET"),
            description=data.get("description", ""),
            headers=json.dumps(data.get("headers", {})),
            body_params=json.dumps(data.get("body_params", {})),
            query_params=json.dumps(data.get("query_params", {})),
        )
        db.session.add(capability)
        db.session.commit()
        return jsonify(capability.to_dict()), 201


@api_bp.route("/mcp-template-capabilities/<int:capability_id>", methods=["GET", "PUT", "DELETE"])
@login_required
def template_capability_detail(capability_id):
    """Get, update, or delete a specific template capability"""
    capability = get_or_404(McpCapabilityTemplate, capability_id)
    template = capability.service_template

    if request.method == "GET":
        return jsonify(capability.to_dict())

    elif request.method == "PUT":
        # Only custom templates can be modified
        if template.template_type != "custom":
            return jsonify({"error": "Cannot modify builtin templates"}), 403

        data = request.get_json()
        capability.name = data.get("name", capability.name)
        capability.capability_type = data.get("capability_type", capability.capability_type)
        capability.endpoint_path = data.get("endpoint_path", capability.endpoint_path)
        capability.method = data.get("method", capability.method)
        capability.description = data.get("description", capability.description)
        capability.headers = json.dumps(data.get("headers", {}))
        capability.body_params = json.dumps(data.get("body_params", {}))
        capability.query_params = json.dumps(data.get("query_params", {}))
        db.session.commit()
        return jsonify(capability.to_dict())

    elif request.method == "DELETE":
        # Only custom templates can be modified
        if template.template_type != "custom":
            return jsonify({"error": "Cannot modify builtin templates"}), 403

        db.session.delete(capability)
        db.session.commit()
        return "", 204


# ============= Variables API =============


@api_bp.route("/variables", methods=["GET", "POST"])
@login_required
def variables():
    """Get all variables or create new variable"""
    if request.method == "GET":
        variables = Variable.query.all()
        return jsonify([v.to_dict() for v in variables])

    elif request.method == "POST":
        data = request.get_json()

        # Check for duplicate name
        if Variable.query.filter_by(name=data["name"]).first():
            return jsonify({"error": "同じ名前の変数が既に存在します"}), 409

        source_type = data.get("source_type", "value")

        variable = Variable(
            name=data["name"],
            value_type=data.get("value_type", "string"),
            source_type=source_type,
            description=data.get("description", ""),
            is_secret=data.get("is_secret", True),
        )

        if source_type == "env":
            variable.env_var_name = data.get("env_var_name", "")
            variable.value = ""  # 環境変数の場合は値を空にする
        else:
            variable.set_value(data["value"])

        db.session.add(variable)
        db.session.commit()
        return jsonify(variable.to_dict()), 201


@api_bp.route("/variables/check-env", methods=["POST"])
@login_required
def check_env_variable():
    """Check if environment variable exists"""
    import os

    data = request.get_json()
    env_var_name = data.get("env_var_name", "")

    if not env_var_name:
        return jsonify({"exists": False}), 200

    # Check if environment variable exists and has a value
    env_value = os.environ.get(env_var_name)
    exists = env_value is not None and env_value != ""

    return jsonify({"exists": exists}), 200


@api_bp.route("/variables/<int:variable_id>", methods=["GET", "PUT", "DELETE"])
@login_required
def variable_detail(variable_id):
    """Get, update, or delete a specific variable"""
    variable = get_or_404(Variable, variable_id)

    if request.method == "GET":
        # include_value=True to show actual value for editing
        return jsonify(variable.to_dict(include_value=True))

    elif request.method == "PUT":
        data = request.get_json()

        # Check for duplicate name (exclude current variable)
        new_name = data.get("name", variable.name)
        if new_name != variable.name:
            existing = Variable.query.filter_by(name=new_name).filter(Variable.id != variable.id).first()
            if existing:
                return jsonify({"error": "同じ名前の変数が既に存在します"}), 409

        variable.name = new_name
        variable.value_type = data.get("value_type", variable.value_type)
        variable.source_type = data.get("source_type", variable.source_type)
        variable.description = data.get("description", variable.description)
        variable.is_secret = data.get("is_secret", variable.is_secret)

        if variable.source_type == "env":
            variable.env_var_name = data.get("env_var_name", variable.env_var_name)
            variable.value = ""  # 環境変数の場合は値を空にする
        else:
            if "value" in data:
                variable.set_value(data["value"])

        db.session.commit()
        return jsonify(variable.to_dict())

    elif request.method == "DELETE":
        db.session.delete(variable)
        db.session.commit()
        return "", 204


# ============= Hierarchical Access Control API =============


@api_bp.route("/mcp-services/<int:mcp_service_id>/access-control", methods=["PUT"])
@login_required
def mcp_service_access_control(mcp_service_id):
    """Toggle MCP service access control (public/restricted)"""
    mcp_service = get_or_404(McpService, mcp_service_id)

    data = request.get_json()
    access_control = data.get("access_control")

    if access_control not in ["public", "restricted"]:
        return jsonify({"error": 'access_control must be "public" or "restricted"'}), 400

    mcp_service.access_control = access_control
    db.session.commit()

    return jsonify(mcp_service.to_dict())


@api_bp.route("/apps/<int:app_id>/access-control", methods=["PUT"])
@login_required
def app_access_control(app_id):
    """Toggle app access control (public/restricted)"""
    app = get_or_404(Service, app_id)

    data = request.get_json()
    access_control = data.get("access_control")

    if access_control not in ["public", "restricted"]:
        return jsonify({"error": 'access_control must be "public" or "restricted"'}), 400

    app.access_control = access_control
    db.session.commit()

    return jsonify(app.to_dict())


@api_bp.route("/capabilities/<int:capability_id>/access-control", methods=["PUT"])
@login_required
def capability_access_control(capability_id):
    """Toggle capability access control (public/restricted)"""
    capability = get_or_404(Capability, capability_id)

    data = request.get_json()
    access_control = data.get("access_control")

    if access_control not in ["public", "restricted"]:
        return jsonify({"error": 'access_control must be "public" or "restricted"'}), 400

    capability.access_control = access_control
    db.session.commit()

    return jsonify(capability.to_dict())


@api_bp.route("/mcp-services/<int:mcp_service_id>/permissions", methods=["GET", "POST"])
@login_required
def mcp_service_permissions(mcp_service_id):
    """Get or add MCP service level permissions"""
    get_or_404(McpService, mcp_service_id)

    if request.method == "GET":
        # Get all accounts with permissions for this MCP service
        permissions = AccountPermission.query.filter_by(mcp_service_id=mcp_service_id).all()
        enabled_account_ids = [p.account_id for p in permissions]

        # Get enabled accounts (with permission)
        enabled_accounts = (
            ConnectionAccount.query.filter(ConnectionAccount.id.in_(enabled_account_ids)).all()
            if enabled_account_ids
            else []
        )

        # Get disabled accounts (without permission)
        disabled_accounts = (
            ConnectionAccount.query.filter(~ConnectionAccount.id.in_(enabled_account_ids)).all()
            if enabled_account_ids
            else ConnectionAccount.query.all()
        )

        return jsonify(
            {"enabled": [a.to_dict() for a in enabled_accounts], "disabled": [a.to_dict() for a in disabled_accounts]}
        )

    elif request.method == "POST":
        data = request.get_json()
        account_ids = data.get("account_ids", [])

        # Delete all existing permissions for this MCP service
        AccountPermission.query.filter_by(mcp_service_id=mcp_service_id).delete()

        # Add new permissions
        for account_id in account_ids:
            # Verify account exists
            account = ConnectionAccount.query.filter_by(id=account_id).first()
            if account:
                permission = AccountPermission(account_id=account_id, mcp_service_id=mcp_service_id)
                db.session.add(permission)

        db.session.commit()
        return jsonify({"message": "MCP service permissions updated"}), 200
        db.session.add(permission)
        db.session.commit()

        return jsonify(permission.to_dict()), 201


@api_bp.route("/apps/<int:app_id>/permissions", methods=["GET", "POST"])
@login_required
def app_permissions(app_id):
    """Get or add app level permissions"""
    get_or_404(Service, app_id)

    if request.method == "GET":
        # Get all accounts with permissions for this app
        permissions = AccountPermission.query.filter_by(app_id=app_id).all()
        enabled_account_ids = [p.account_id for p in permissions]

        # Get enabled accounts (with permission)
        enabled_accounts = (
            ConnectionAccount.query.filter(ConnectionAccount.id.in_(enabled_account_ids)).all()
            if enabled_account_ids
            else []
        )

        # Get disabled accounts (without permission)
        disabled_accounts = (
            ConnectionAccount.query.filter(~ConnectionAccount.id.in_(enabled_account_ids)).all()
            if enabled_account_ids
            else ConnectionAccount.query.all()
        )

        return jsonify(
            {"enabled": [a.to_dict() for a in enabled_accounts], "disabled": [a.to_dict() for a in disabled_accounts]}
        )

    elif request.method == "POST":
        data = request.get_json()
        account_ids = data.get("account_ids", [])

        # Delete all existing permissions for this app
        AccountPermission.query.filter_by(app_id=app_id).delete()

        # Add new permissions
        for account_id in account_ids:
            # Verify account exists
            account = ConnectionAccount.query.filter_by(id=account_id).first()
            if account:
                permission = AccountPermission(account_id=account_id, app_id=app_id)
                db.session.add(permission)

        db.session.commit()
        return jsonify({"message": "App permissions updated"}), 200


@api_bp.route("/accounts/<int:account_id>/permissions/by-level", methods=["GET"])
@login_required
def account_permissions_by_level(account_id):
    """Get account permissions grouped by level (mcp_service, app, capability)"""
    get_or_404(ConnectionAccount, account_id)

    permissions = AccountPermission.query.filter_by(account_id=account_id).all()

    result: dict[str, list[dict]] = {"mcp_service": [], "app": [], "capability": []}

    for perm in permissions:
        level = perm.get_permission_level()
        if level:
            result[level].append(perm.to_dict())

    return jsonify(result)


# ============= Connection Logs API =============


@api_bp.route("/connection-logs", methods=["GET"])
@login_required
def connection_logs():
    """Get connection logs with filtering and pagination"""
    # Pagination
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 50, type=int)
    per_page = min(per_page, 100)  # Max 100 per page

    # Build query
    query = McpConnectionLog.query

    # Filter by mcp_service_id
    mcp_service_id = request.args.get("mcp_service_id", type=int)
    if mcp_service_id:
        query = query.filter(McpConnectionLog.mcp_service_id == mcp_service_id)

    # Filter by account_id
    account_id = request.args.get("account_id", type=int)
    if account_id:
        query = query.filter(McpConnectionLog.account_id == account_id)

    # Filter by mcp_method
    mcp_method = request.args.get("mcp_method")
    if mcp_method:
        query = query.filter(McpConnectionLog.mcp_method == mcp_method)

    # Filter by is_success
    is_success = request.args.get("is_success")
    if is_success is not None:
        query = query.filter(McpConnectionLog.is_success == (is_success.lower() == "true"))

    # Full-text search in request_body and response_body
    search = request.args.get("search")
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            db.or_(
                McpConnectionLog.request_body.ilike(search_pattern),
                McpConnectionLog.response_body.ilike(search_pattern),
                McpConnectionLog.mcp_method.ilike(search_pattern),
            )
        )

    # Filter by date range
    date_from_str = request.args.get("date_from")
    if date_from_str:
        try:
            date_from = datetime.fromisoformat(date_from_str.replace("Z", "+00:00"))
            query = query.filter(McpConnectionLog.created_at >= date_from)
        except ValueError:
            pass

    date_to_str = request.args.get("date_to")
    if date_to_str:
        try:
            date_to = datetime.fromisoformat(date_to_str.replace("Z", "+00:00"))
            query = query.filter(McpConnectionLog.created_at <= date_to)
        except ValueError:
            pass

    # Order by created_at descending
    query = query.order_by(McpConnectionLog.created_at.desc())

    # Paginate
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return jsonify(
        {
            "items": [log.to_dict() for log in pagination.items],
            "total": pagination.total,
            "page": pagination.page,
            "per_page": pagination.per_page,
            "pages": pagination.pages,
            "has_next": pagination.has_next,
            "has_prev": pagination.has_prev,
        }
    )


@api_bp.route("/connection-logs/by-service", methods=["GET"])
@login_required
def connection_logs_by_service():
    """Get log counts grouped by MCP service"""

    # Get all MCP services with log counts
    mcp_services = McpService.query.all()

    result = []
    for service in mcp_services:
        log_count = McpConnectionLog.query.filter_by(mcp_service_id=service.id).count()

        # Get last log time
        last_log = (
            McpConnectionLog.query.filter_by(mcp_service_id=service.id)
            .order_by(McpConnectionLog.created_at.desc())
            .first()
        )

        result.append(
            {
                "mcp_service": service.to_dict(),
                "log_count": log_count,
                "last_log_at": last_log.created_at.isoformat() if last_log else None,
            }
        )

    # Also include logs without mcp_service (orphaned)
    orphan_count = McpConnectionLog.query.filter_by(mcp_service_id=None).count()
    if orphan_count > 0:
        last_orphan = (
            McpConnectionLog.query.filter_by(mcp_service_id=None).order_by(McpConnectionLog.created_at.desc()).first()
        )
        result.append(
            {
                "mcp_service": None,
                "mcp_service_name": "その他（サービス削除済み）",
                "log_count": orphan_count,
                "last_log_at": last_orphan.created_at.isoformat() if last_orphan else None,
            }
        )

    return jsonify(result)


@api_bp.route("/connection-logs/<int:log_id>", methods=["GET"])
@login_required
def connection_log_detail(log_id):
    """Get a specific connection log with full details"""
    log = get_or_404(McpConnectionLog, log_id)
    return jsonify(log.to_dict(include_bodies=True))


@api_bp.route("/connection-logs/export", methods=["GET"])
@login_required
def connection_logs_export():
    """Export connection logs as CSV"""
    from flask import Response

    # Build query with same filters as list endpoint
    query = McpConnectionLog.query

    mcp_service_id = request.args.get("mcp_service_id", type=int)
    if mcp_service_id:
        query = query.filter(McpConnectionLog.mcp_service_id == mcp_service_id)

    account_id = request.args.get("account_id", type=int)
    if account_id:
        query = query.filter(McpConnectionLog.account_id == account_id)

    mcp_method = request.args.get("mcp_method")
    if mcp_method:
        query = query.filter(McpConnectionLog.mcp_method == mcp_method)

    is_success = request.args.get("is_success")
    if is_success is not None:
        query = query.filter(McpConnectionLog.is_success == (is_success.lower() == "true"))

    date_from_str = request.args.get("date_from")
    if date_from_str:
        try:
            date_from = datetime.fromisoformat(date_from_str.replace("Z", "+00:00"))
            query = query.filter(McpConnectionLog.created_at >= date_from)
        except ValueError:
            pass

    date_to_str = request.args.get("date_to")
    if date_to_str:
        try:
            date_to = datetime.fromisoformat(date_to_str.replace("Z", "+00:00"))
            query = query.filter(McpConnectionLog.created_at <= date_to)
        except ValueError:
            pass

    query = query.order_by(McpConnectionLog.created_at.desc())

    # Limit to 10000 rows for export
    logs = query.limit(10000).all()

    # Generate CSV
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(McpConnectionLog.csv_headers())
    for log in logs:
        writer.writerow(log.to_csv_row())

    # Return as downloadable CSV
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=connection_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        },
    )


@api_bp.route("/connection-logs/cleanup", methods=["DELETE"])
@login_required
def connection_logs_cleanup():
    """Delete logs older than specified days"""
    days = request.args.get("days", 90, type=int)

    if days < 1:
        return jsonify({"error": "Days must be at least 1"}), 400

    cutoff_date = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days)

    # Count and delete
    count = McpConnectionLog.query.filter(McpConnectionLog.created_at < cutoff_date).count()
    McpConnectionLog.query.filter(McpConnectionLog.created_at < cutoff_date).delete()
    db.session.commit()

    return jsonify({"deleted_count": count, "cutoff_date": cutoff_date.isoformat()})


@api_bp.route("/admin/log-settings", methods=["GET", "PUT"])
@login_required
def log_settings():
    """Get or update log settings"""
    setting_keys = [
        "mcp_log_enabled",
        "mcp_log_retention_days",
        "mcp_log_max_body_size",
        "mcp_log_mask_credit_card",
        "mcp_log_mask_email",
        "mcp_log_mask_phone",
        "mcp_log_mask_custom_patterns",
    ]

    if request.method == "GET":
        result = {}
        for key in setting_keys:
            setting = AdminSettings.query.filter_by(setting_key=key).first()
            if setting:
                value = setting.setting_value
                # Parse boolean and numeric values
                if value.lower() in ("true", "false"):
                    result[key] = value.lower() == "true"
                elif value.isdigit():
                    result[key] = int(value)
                else:
                    result[key] = value
            else:
                # Defaults
                defaults = {
                    "mcp_log_enabled": True,
                    "mcp_log_retention_days": 90,
                    "mcp_log_max_body_size": 10240,
                    "mcp_log_mask_credit_card": True,
                    "mcp_log_mask_email": True,
                    "mcp_log_mask_phone": True,
                    "mcp_log_mask_custom_patterns": "",
                }
                result[key] = defaults.get(key)

        return jsonify(result)

    elif request.method == "PUT":
        data = request.get_json()

        for key in setting_keys:
            if key in data:
                value = data[key]
                # Convert to string for storage
                value = ("true" if value else "false") if isinstance(value, bool) else str(value)

                setting = AdminSettings.query.filter_by(setting_key=key).first()
                if setting:
                    setting.setting_value = value
                else:
                    setting = AdminSettings(setting_key=key, setting_value=value)
                    db.session.add(setting)

        db.session.commit()

        return jsonify({"message": "Settings updated successfully"})


@api_bp.route("/connection-logs/stats", methods=["GET"])
@login_required
def connection_logs_stats():
    """Get connection log statistics"""
    from sqlalchemy import func

    mcp_service_id = request.args.get("mcp_service_id", type=int)

    # Base query
    query = McpConnectionLog.query
    if mcp_service_id:
        query = query.filter(McpConnectionLog.mcp_service_id == mcp_service_id)

    # Total count
    total_count = query.count()

    # Success/Error counts
    success_count = query.filter(McpConnectionLog.is_success).count()
    error_count = query.filter(McpConnectionLog.is_success == False).count()  # noqa: E712

    # Method distribution
    method_stats = (
        db.session.query(McpConnectionLog.mcp_method, func.count(McpConnectionLog.id))
        .group_by(McpConnectionLog.mcp_method)
        .all()
    )

    # Last 24 hours count
    last_24h = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=24)
    last_24h_count = query.filter(McpConnectionLog.created_at >= last_24h).count()

    return jsonify(
        {
            "total": total_count,
            "success": success_count,
            "error": error_count,
            "last_24h": last_24h_count,
            "by_method": dict(method_stats),
        }
    )


# ============= Admin Login Logs API =============


@api_bp.route("/admin/login-logs", methods=["GET"])
@login_required
def admin_login_logs():
    """Get admin login logs with filtering"""
    from app.models.models import AdminLoginLog

    # Pagination
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 50, type=int)

    # Filters
    query = AdminLoginLog.query

    username = request.args.get("username")
    if username:
        query = query.filter(AdminLoginLog.username == username)

    ip_address = request.args.get("ip_address")
    if ip_address:
        query = query.filter(AdminLoginLog.ip_address == ip_address)

    is_success = request.args.get("is_success")
    if is_success is not None:
        query = query.filter(AdminLoginLog.is_success == (is_success.lower() == "true"))

    date_from = request.args.get("date_from")
    if date_from:
        try:
            date_from_obj = datetime.fromisoformat(date_from.replace("Z", "+00:00"))
            query = query.filter(AdminLoginLog.created_at >= date_from_obj)
        except ValueError:
            pass

    date_to = request.args.get("date_to")
    if date_to:
        try:
            date_to_obj = datetime.fromisoformat(date_to.replace("Z", "+00:00"))
            query = query.filter(AdminLoginLog.created_at <= date_to_obj)
        except ValueError:
            pass

    # Order by created_at desc
    query = query.order_by(AdminLoginLog.created_at.desc())

    # Paginate
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return jsonify(
        {
            "logs": [log.to_dict() for log in pagination.items],
            "total": pagination.total,
            "pages": pagination.pages,
            "current_page": page,
            "per_page": per_page,
        }
    )


@api_bp.route("/admin/login-logs/export", methods=["GET"])
@login_required
def export_admin_login_logs():
    """Export admin login logs as CSV"""
    from app.models.models import AdminLoginLog

    query = AdminLoginLog.query.order_by(AdminLoginLog.created_at.desc()).limit(10000)
    logs = query.all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(AdminLoginLog.csv_headers())
    for log in logs:
        writer.writerow(log.to_csv_row())

    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=admin_login_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        },
    )


# ============= Admin Action Logs API =============


@api_bp.route("/admin/action-logs", methods=["GET"])
@login_required
def admin_action_logs():
    """Get admin action logs with filtering"""
    from app.models.models import AdminActionLog

    # Pagination
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 50, type=int)

    # Filters
    query = AdminActionLog.query

    admin_username = request.args.get("admin_username")
    if admin_username:
        query = query.filter(AdminActionLog.admin_username == admin_username)

    action_type = request.args.get("action_type")
    if action_type:
        query = query.filter(AdminActionLog.action_type == action_type)

    resource_type = request.args.get("resource_type")
    if resource_type:
        query = query.filter(AdminActionLog.resource_type == resource_type)

    date_from = request.args.get("date_from")
    if date_from:
        try:
            date_from_obj = datetime.fromisoformat(date_from.replace("Z", "+00:00"))
            query = query.filter(AdminActionLog.created_at >= date_from_obj)
        except ValueError:
            pass

    date_to = request.args.get("date_to")
    if date_to:
        try:
            date_to_obj = datetime.fromisoformat(date_to.replace("Z", "+00:00"))
            query = query.filter(AdminActionLog.created_at <= date_to_obj)
        except ValueError:
            pass

    # Order by created_at desc
    query = query.order_by(AdminActionLog.created_at.desc())

    # Paginate
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return jsonify(
        {
            "logs": [log.to_dict() for log in pagination.items],
            "total": pagination.total,
            "pages": pagination.pages,
            "current_page": page,
            "per_page": per_page,
        }
    )


@api_bp.route("/admin/action-logs/export", methods=["GET"])
@login_required
def export_admin_action_logs():
    """Export admin action logs as CSV"""
    from app.models.models import AdminActionLog

    query = AdminActionLog.query.order_by(AdminActionLog.created_at.desc()).limit(10000)
    logs = query.all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(AdminActionLog.csv_headers())
    for log in logs:
        writer.writerow(log.to_csv_row())

    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=admin_action_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        },
    )


@api_bp.route("/admin/unlock-account", methods=["POST"])
@login_required
def unlock_account():
    """Manually unlock a locked IP address"""
    from app.models.models import LoginLockStatus

    data = request.get_json()
    ip_address = data.get("ip_address")

    if not ip_address:
        return jsonify({"error": "IP address is required"}), 400

    lock_status = LoginLockStatus.query.filter_by(ip_address=ip_address).first()
    if not lock_status:
        return jsonify({"error": "No lock status found for this IP"}), 404

    # Reset lock
    lock_status.failed_attempts = 0
    lock_status.locked_until = None
    lock_status.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.session.commit()

    return jsonify({"message": f"IP {ip_address} has been unlocked", "lock_status": lock_status.to_dict()})


@api_bp.route("/admin/locked-ips", methods=["GET"])
@login_required
def get_locked_ips():
    """Get list of currently locked IP addresses"""
    from app.models.models import LoginLockStatus

    # Get all locked IPs (where locked_until is in the future)
    locked = LoginLockStatus.query.filter(
        LoginLockStatus.locked_until > datetime.now(timezone.utc).replace(tzinfo=None)
    ).all()

    return jsonify({"locked_ips": [lock.to_dict() for lock in locked], "total": len(locked)})


# ============= Template Sync API =============


@api_bp.route("/templates/check-updates", methods=["GET"])
@login_required
def check_template_updates():
    """Check for template updates from GitHub repository"""
    from app.services.template_sync import TemplateNotFoundError, TemplateSyncService, VersionIncompatibleError

    try:
        service = TemplateSyncService()
        update_info = service.check_for_updates()
        return jsonify(update_info)
    except VersionIncompatibleError as e:
        return jsonify({"error": str(e), "type": "incompatible"}), 400
    except TemplateNotFoundError as e:
        return jsonify({"error": str(e), "type": "not_found"}), 404
    except Exception as e:
        return jsonify({"error": f"Update check failed: {str(e)}", "type": "unknown"}), 500


@api_bp.route("/templates/sync", methods=["POST"])
@login_required
@audit_log("template", action_type="sync")
def sync_templates():
    """Synchronize templates from GitHub repository"""
    from app.services.template_sync import TemplateNotFoundError, TemplateSyncService, VersionIncompatibleError

    try:
        service = TemplateSyncService()
        result = service.sync_templates()
        return jsonify(result)
    except VersionIncompatibleError as e:
        return jsonify({"error": str(e), "type": "incompatible"}), 400
    except TemplateNotFoundError as e:
        return jsonify({"error": str(e), "type": "not_found"}), 404
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Template sync failed: {str(e)}", "type": "unknown"}), 500


# ============= Resource Management API =============


@api_bp.route("/resources", methods=["GET", "POST"])
@login_required
@audit_log("resource", action_type="create", get_resource_name=lambda d: d.get("name"))
def resources():
    """Get all resources or create new resource"""
    if request.method == "GET":
        resources = Resource.query.all()
        return jsonify([r.to_dict(include_usage=True) for r in resources])

    elif request.method == "POST":
        data = request.get_json()

        # Generate unique resource_id
        resource_id = Resource.generate_resource_id()

        resource = Resource(
            resource_id=resource_id,
            name=data["name"],
            description=data.get("description", ""),
            mime_type=data.get("mime_type", "text/plain"),
            content=data.get("content", ""),
            access_control=data.get("access_control", "restricted"),
            is_enabled=data.get("is_enabled", True),
        )

        db.session.add(resource)
        db.session.flush()  # Assign resource.id without committing, so a failure below leaves nothing behind

        # Add account permissions if restricted
        if resource.access_control == "restricted" and "account_ids" in data:
            for account_id in data["account_ids"]:
                access = ResourceAccountAccess(resource_id=resource.id, account_id=account_id)
                db.session.add(access)
        db.session.commit()

        return jsonify(resource.to_dict()), 201


@api_bp.route("/resources/<int:resource_id>", methods=["GET", "PUT", "DELETE"])
@login_required
@audit_log("resource", get_resource_name=lambda d: d.get("name"))
def resource_detail(resource_id):
    """Get, update, or delete a specific resource"""
    resource = get_or_404(Resource, resource_id)

    if request.method == "GET":
        result = resource.to_dict(include_usage=True)
        # Include account access list
        result["account_ids"] = [access.account_id for access in resource.resource_account_access]
        return jsonify(result)

    elif request.method == "PUT":
        data = request.get_json()

        resource.name = data.get("name", resource.name)
        resource.description = data.get("description", resource.description)
        resource.mime_type = data.get("mime_type", resource.mime_type)
        resource.content = data.get("content", resource.content)
        resource.access_control = data.get("access_control", resource.access_control)
        resource.is_enabled = data.get("is_enabled", resource.is_enabled)

        # Update account permissions
        if "account_ids" in data:
            # Remove existing permissions
            ResourceAccountAccess.query.filter_by(resource_id=resource.id).delete()

            # Add new permissions if restricted
            if resource.access_control == "restricted":
                for account_id in data["account_ids"]:
                    access = ResourceAccountAccess(resource_id=resource.id, account_id=account_id)
                    db.session.add(access)

        db.session.commit()
        return jsonify(resource.to_dict())

    elif request.method == "DELETE":
        # Check if resource is being used by any capability
        usage_count = resource.get_usage_count()
        if usage_count > 0:
            return jsonify(
                {
                    "error": f"このResourceは{usage_count}個のCapabilityで使用されています。削除する前に、参照しているCapabilityを削除または別のResourceに変更してください。"
                }
            ), 409

        db.session.delete(resource)
        db.session.commit()
        return "", 204


@api_bp.route("/resources/<int:resource_id>/toggle", methods=["POST"])
@login_required
@audit_log("resource", action_type="update")
def toggle_resource(resource_id):
    """Toggle resource enabled/disabled status"""
    resource = get_or_404(Resource, resource_id)
    resource.is_enabled = not resource.is_enabled
    db.session.commit()
    return jsonify(resource.to_dict())


@api_bp.route("/resources/<int:resource_id>/access-control", methods=["PUT"])
@login_required
@audit_log("resource", action_type="update")
def resource_access_control(resource_id):
    """Update resource access control"""
    resource = get_or_404(Resource, resource_id)

    data = request.get_json()
    access_control = data.get("access_control")

    if access_control not in ["public", "restricted"]:
        return jsonify({"error": "Invalid access control value"}), 400

    resource.access_control = access_control

    # If changing to public, remove all account permissions
    if access_control == "public":
        ResourceAccountAccess.query.filter_by(resource_id=resource.id).delete()

    db.session.commit()
    return jsonify(resource.to_dict())


# ============= Admin Credentials API =============


@api_bp.route("/admin/credentials", methods=["POST"])
@login_required
def update_admin_credentials():
    """Update the currently logged-in admin's own login credentials and/or the
    Admin MCP API key.

    Request body (all fields optional):
      {
        "username": "new_username",
        "password": "new_password",
        "admin_api_key": "new_bearer_token"
      }

    On success marks AdminCredentials.is_initialized = True.
    """
    from app.controllers.auth_controller import _get_current_admin_credentials

    data = request.get_json() or {}

    new_username = data.get("username", "").strip()
    new_password = data.get("password", "").strip()
    new_api_key = data.get("admin_api_key", "").strip()

    if not new_username and not new_password and not new_api_key:
        return jsonify({"error": "username, password, admin_api_key のいずれかを指定してください"}), 400

    cred = _get_current_admin_credentials()
    if cred is None:
        return jsonify({"error": "管理者資格情報が存在しません"}), 404

    if new_username:
        if len(new_username) > 100:
            return jsonify({"error": "ユーザー名は100文字以内にしてください"}), 400
        existing = AdminCredentials.query.filter(
            AdminCredentials.username == new_username, AdminCredentials.id != cred.id
        ).first()
        if existing:
            return jsonify({"error": "同じユーザー名の管理者が既に存在します"}), 409
        cred.username = new_username

    if new_password:
        if len(new_password) < 8:
            return jsonify({"error": "パスワードは8文字以上にしてください"}), 400
        cred.set_password(new_password)

    if new_api_key:
        if len(new_api_key) < 16:
            return jsonify({"error": "Admin MCP APIキーは16文字以上にしてください"}), 400
        system_account = ConnectionAccount.query.filter_by(is_system=True).first()
        if system_account is None:
            return jsonify({"error": "システムアカウントが見つかりません"}), 404
        system_account.bearer_token = new_api_key

    cred.is_initialized = True
    db.session.commit()

    # Keep the session in sync if the username changed, so login_required
    # keeps recognizing the currently logged-in admin on subsequent requests.
    if new_username:
        session["admin_username"] = cred.username

    return jsonify({"success": True, "message": "資格情報を更新しました"})


# ============= Admin User (Web Login Accounts) API =============


@api_bp.route("/admin-users", methods=["GET", "POST"])
@login_required
@audit_log("admin_user", action_type="create", get_resource_name=lambda d: d.get("username"))
def admin_users():
    """List all admin (web UI login) accounts, or create a new one."""
    if request.method == "GET":
        users = AdminCredentials.query.order_by(AdminCredentials.created_at).all()
        return jsonify([u.to_dict() for u in users])

    elif request.method == "POST":
        data = request.get_json() or {}
        username = data.get("username", "").strip()
        password = data.get("password", "").strip()

        if not username:
            return jsonify({"error": "ユーザー名を入力してください"}), 400
        if len(username) > 100:
            return jsonify({"error": "ユーザー名は100文字以内にしてください"}), 400
        if len(password) < 8:
            return jsonify({"error": "パスワードは8文字以上にしてください"}), 400
        if AdminCredentials.query.filter_by(username=username).first():
            return jsonify({"error": "同じユーザー名の管理者が既に存在します"}), 409

        # Admins created here are set up directly by another admin, so they
        # don't need to go through the forced first-login credential change.
        cred = AdminCredentials(username=username, is_initialized=True)
        cred.set_password(password)
        db.session.add(cred)
        db.session.commit()
        return jsonify(cred.to_dict()), 201


@api_bp.route("/admin-users/<int:user_id>", methods=["GET", "PUT", "DELETE"])
@login_required
@audit_log("admin_user", get_resource_name=lambda d: d.get("username"))
def admin_user_detail(user_id):
    """Get, update, or delete a specific admin (web UI login) account."""
    cred = get_or_404(AdminCredentials, user_id)

    if request.method == "GET":
        return jsonify(cred.to_dict())

    elif request.method == "PUT":
        data = request.get_json() or {}
        new_username = data.get("username", "").strip()
        new_password = data.get("password", "").strip()
        old_username = cred.username

        if new_username and new_username != cred.username:
            if len(new_username) > 100:
                return jsonify({"error": "ユーザー名は100文字以内にしてください"}), 400
            existing = AdminCredentials.query.filter(
                AdminCredentials.username == new_username, AdminCredentials.id != cred.id
            ).first()
            if existing:
                return jsonify({"error": "同じユーザー名の管理者が既に存在します"}), 409
            cred.username = new_username

        if new_password:
            if len(new_password) < 8:
                return jsonify({"error": "パスワードは8文字以上にしてください"}), 400
            cred.set_password(new_password)

        db.session.commit()

        # Keep the session in sync if the currently logged-in admin edited
        # their own account through this screen.
        if session.get("admin_username") == old_username:
            session["admin_username"] = cred.username

        return jsonify(cred.to_dict())

    elif request.method == "DELETE":
        if AdminCredentials.query.count() <= 1:
            return jsonify({"error": "最後の管理者アカウントは削除できません"}), 400
        if session.get("admin_username") == cred.username:
            return jsonify({"error": "ログイン中の自分のアカウントは削除できません"}), 400

        db.session.delete(cred)
        db.session.commit()
        return "", 204


@api_bp.route("/admin/system-account", methods=["GET"])
@login_required
def get_system_account():
    """Get system account (Admin MCP API key) info."""
    system_account = ConnectionAccount.query.filter_by(is_system=True).first()
    if system_account is None:
        return jsonify({"error": "システムアカウントが見つかりません"}), 404
    return jsonify(
        {
            "id": system_account.id,
            "bearer_token": system_account.bearer_token,
        }
    )


@api_bp.route("/admin/system-account/regenerate", methods=["POST"])
@login_required
def regenerate_system_account_token():
    """Regenerate the Admin MCP API key (system account bearer token)."""
    system_account = ConnectionAccount.query.filter_by(is_system=True).first()
    if system_account is None:
        return jsonify({"error": "システムアカウントが見つかりません"}), 404
    system_account.bearer_token = secrets.token_urlsafe(32)
    db.session.commit()
    return jsonify({"success": True, "bearer_token": system_account.bearer_token})
