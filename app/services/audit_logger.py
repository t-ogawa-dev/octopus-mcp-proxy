"""
Audit Logger Service
Handles logging of admin CRUD operations for security audit trails
"""

import contextlib
import json
import logging
from datetime import datetime, timezone
from functools import wraps

from flask import request, session

from app.services.background import BoundedExecutor

logger = logging.getLogger(__name__)

# Thread pool for async log writing
_executor = BoundedExecutor(max_workers=2, max_pending=1000, name="audit-log")


def _get_client_ip():
    """Get client IP address from request.

    X-Forwarded-For is resolved by ProxyFix only for the configured number of trusted
    proxies (TRUSTED_PROXY_COUNT), so a client cannot spoof its address with the header.
    """
    return request.remote_addr or "0.0.0.0"


def _log_admin_action(
    admin_username,
    action_type,
    resource_type,
    resource_id=None,
    resource_name=None,
    changes=None,
    ip_address=None,
    user_agent=None,
):
    """Log admin action asynchronously (or synchronously in test mode)"""
    import os

    from flask import current_app

    # Captured here because the worker thread has no application context of its own
    app = current_app._get_current_object()

    def _write_log():
        try:
            from app.models.models import AdminActionLog, db

            with app.app_context():
                log_entry = AdminActionLog(
                    created_at=datetime.now(timezone.utc).replace(tzinfo=None),
                    admin_username=admin_username,
                    action_type=action_type,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    resource_name=resource_name,
                    changes=json.dumps(changes, ensure_ascii=False) if changes else None,
                    ip_address=ip_address,
                    user_agent=user_agent,
                )
                db.session.add(log_entry)
                db.session.commit()
                logger.debug(f"Admin action logged: {admin_username} {action_type} {resource_type} #{resource_id}")
        except Exception as e:
            logger.error(f"Failed to log admin action: {e}")

    # In test mode, execute synchronously
    if os.environ.get("TESTING") or app.config.get("TESTING"):
        _write_log()
    else:
        _executor.submit(_write_log)


def audit_log(resource_type, action_type=None, get_resource_name=None):
    """
    Decorator to log admin CRUD operations

    Args:
        resource_type: Type of resource ('mcp_service', 'app', 'capability', 'account', etc.)
        action_type: Action type ('create', 'update', 'delete'). If None, inferred from HTTP method
        get_resource_name: Function to extract resource name from response data

    Usage:
        @audit_log('mcp_service', get_resource_name=lambda data: data.get('name'))
        def create_mcp_service():
            ...
    """

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Get admin username from session
            admin_username = session.get("admin_username", "accel")
            ip_address = _get_client_ip()
            user_agent = request.headers.get("User-Agent", "")[:500]

            # Infer action type from HTTP method if not provided
            inferred_action = action_type
            if inferred_action is None:
                method_map = {"POST": "create", "PUT": "update", "PATCH": "update", "DELETE": "delete"}
                inferred_action = method_map.get(request.method, "unknown")

            # For UPDATE/DELETE, capture before state
            resource_id = kwargs.get(f"{resource_type}_id") or kwargs.get("id")
            before_data = None

            if inferred_action in ["update", "delete"] and resource_id:
                # Store before state in g for comparison
                try:
                    from app.models.models import (
                        AccountPermission,
                        Capability,
                        ConnectionAccount,
                        McpService,
                        Service,
                        db,
                    )

                    model_map = {
                        "mcp_service": McpService,
                        "app": Service,
                        "capability": Capability,
                        "account": ConnectionAccount,
                        "permission": AccountPermission,
                    }

                    model = model_map.get(resource_type)
                    if model:
                        obj = db.session.get(model, resource_id)
                        if obj:
                            before_data = obj.to_dict()
                except Exception as e:
                    logger.warning(f"Failed to capture before state: {e}")

            # Execute the original function
            response = f(*args, **kwargs)

            # Extract response data
            if hasattr(response, "get_json"):
                response_data = response.get_json()
            elif isinstance(response, tuple) and len(response) > 0:
                if hasattr(response[0], "get_json"):
                    response_data = response[0].get_json()
                else:
                    response_data = response[0] if isinstance(response[0], dict) else {}
            elif isinstance(response, dict):
                response_data = response
            else:
                response_data = {}

            # Determine resource ID and name
            # Skip audit logging for list responses (GET requests typically return lists)
            if not resource_id and response_data and isinstance(response_data, dict):
                resource_id = response_data.get("id")

            resource_name = None
            if get_resource_name and response_data and isinstance(response_data, dict):
                with contextlib.suppress(BaseException):
                    resource_name = get_resource_name(response_data)

            if not resource_name and response_data and isinstance(response_data, dict):
                resource_name = response_data.get("name") or response_data.get("username")

            # Calculate changes for UPDATE
            changes = None
            if inferred_action == "update" and before_data and response_data and isinstance(response_data, dict):
                changes = {}
                for key, new_value in response_data.items():
                    old_value = before_data.get(key)
                    if old_value != new_value and key not in ["updated_at", "created_at"]:
                        changes[key] = {"old": old_value, "new": new_value}
            elif inferred_action == "create" and response_data and isinstance(response_data, dict):
                # For CREATE, log the created values
                changes = {
                    k: {"new": v} for k, v in response_data.items() if k not in ["id", "created_at", "updated_at"]
                }
            elif inferred_action == "delete" and before_data:
                # For DELETE, log the deleted values
                changes = {k: {"old": v} for k, v in before_data.items()}

            # Log the action
            _log_admin_action(
                admin_username=admin_username,
                action_type=inferred_action,
                resource_type=resource_type,
                resource_id=resource_id,
                resource_name=resource_name,
                changes=changes,
                ip_address=ip_address,
                user_agent=user_agent,
            )

            return response

        return decorated_function

    return decorator


def shutdown_logger():
    """Shutdown the thread pool executor gracefully"""
    _executor.shutdown(wait=True)
