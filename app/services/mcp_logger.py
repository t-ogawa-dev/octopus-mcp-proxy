"""
MCP Connection Logger Service
Handles async logging of MCP requests with sensitive data masking.
Outputs structured JSON logs to stdout for container log aggregation.
"""

import json
import logging
import os
import re
import sys
import time
from datetime import datetime, timezone
from typing import Any

from flask import Flask

from app.services.background import BoundedExecutor

logger = logging.getLogger(__name__)

# Thread pool for async log writing; excess entries are dropped rather than queued without limit
_executor = BoundedExecutor(max_workers=3, max_pending=5000, name="mcp-log")

# Stdout logging configuration
STDOUT_LOGGING_ENABLED = os.getenv("MCP_LOG_STDOUT", "true").lower() == "true"


# Default masking patterns
MASK_PATTERNS = {
    "credit_card": r"\b(?:\d{4}[-\s]?){3}\d{4}\b",  # 16-digit card numbers
    "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
    "phone": r"\b(?:\+?1[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)?\d{3}[-.\s]?\d{4}\b",
}

MASK_REPLACEMENT = "[MASKED]"
# Keys containing any of these (after removing non-alphanumerics) are masked
SENSITIVE_LOG_FIELDS = ("authorization", "password", "passwd", "secret", "credential", "apikey", "privatekey")
# Keys ending with these are masked; "token" alone would also hit max_tokens, tokenizer, ...
SENSITIVE_LOG_SUFFIXES = ("token",)


def _is_sensitive_key(key: Any) -> bool:
    normalized_key = re.sub(r"[^a-z0-9]", "", str(key).lower())
    return any(field in normalized_key for field in SENSITIVE_LOG_FIELDS) or normalized_key.endswith(
        SENSITIVE_LOG_SUFFIXES
    )


class LogContext:
    """Context object to track request timing and metadata"""

    def __init__(self):
        self.start_time: float | None = None
        self.mcp_service_id: int | None = None
        self.mcp_service_name: str | None = None
        self.app_id: int | None = None
        self.app_name: str | None = None
        self.capability_id: int | None = None
        self.capability_name: str | None = None
        self.account_id: int | None = None
        self.account_name: str | None = None
        self.mcp_method: str | None = None
        self.tool_name: str | None = None
        self.request_id: str | None = None
        self.ip_address: str | None = None
        self.user_agent: str | None = None
        self.access_control: str | None = None
        self.request_body: str | None = None

    def start(self):
        """Start timing the request"""
        self.start_time = time.time()
        return self

    def get_duration_ms(self) -> int | None:
        """Get duration in milliseconds"""
        if self.start_time is None:
            return None
        return int((time.time() - self.start_time) * 1000)


def get_log_settings(app: Flask) -> dict[str, Any]:
    """Get log settings from AdminSettings table"""
    with app.app_context():
        from app.models.models import AdminSettings

        settings = {}
        keys = [
            "mcp_log_enabled",
            "mcp_log_retention_days",
            "mcp_log_max_body_size",
            "mcp_log_mask_credit_card",
            "mcp_log_mask_email",
            "mcp_log_mask_phone",
            "mcp_log_mask_custom_patterns",
        ]

        for key in keys:
            setting = AdminSettings.query.filter_by(setting_key=key).first()
            if setting:
                # Parse boolean and numeric values
                value = setting.setting_value
                if value.lower() in ("true", "false"):
                    settings[key] = value.lower() == "true"
                elif value.isdigit():
                    settings[key] = int(value)
                else:
                    settings[key] = value
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
                settings[key] = defaults.get(key)

        return settings


def mask_sensitive_data(text: str, settings: dict[str, Any]) -> str:
    """Apply masking patterns to sensitive data in text"""
    if not text:
        return text

    masked = text

    def mask_json_value(value: Any) -> tuple[Any, bool]:
        if isinstance(value, dict):
            masked_dict: dict[Any, Any] = {}
            changed = False
            for key, item in value.items():
                if _is_sensitive_key(key):
                    masked_dict[key] = MASK_REPLACEMENT
                    changed = True
                else:
                    masked_dict[key], item_changed = mask_json_value(item)
                    changed = changed or item_changed
            return masked_dict, changed
        if isinstance(value, list):
            masked_list: list[Any] = []
            changed = False
            for item in value:
                masked_item, item_changed = mask_json_value(item)
                masked_list.append(masked_item)
                changed = changed or item_changed
            return masked_list, changed
        if isinstance(value, str):
            bearer_masked = re.sub(r"(?i)\bBearer\s+[^\s,;\"']+", f"Bearer {MASK_REPLACEMENT}", value)
            return bearer_masked, bearer_masked != value
        return value, False

    try:
        parsed = json.loads(masked)
    except (json.JSONDecodeError, TypeError):
        parsed = None
        json_changed = False
    else:
        parsed, json_changed = mask_json_value(parsed)
        if json_changed:
            masked = json.dumps(parsed, ensure_ascii=False)

    if not json_changed:
        masked = re.sub(r"(?i)\bBearer\s+[^\s,;\"']+", f"Bearer {MASK_REPLACEMENT}", masked)

    # Apply preset masks
    if settings.get("mcp_log_mask_credit_card", True):
        masked = re.sub(MASK_PATTERNS["credit_card"], MASK_REPLACEMENT, masked)

    if settings.get("mcp_log_mask_email", True):
        masked = re.sub(MASK_PATTERNS["email"], MASK_REPLACEMENT, masked, flags=re.IGNORECASE)

    if settings.get("mcp_log_mask_phone", True):
        masked = re.sub(MASK_PATTERNS["phone"], MASK_REPLACEMENT, masked)

    # Apply custom patterns (one pattern per line)
    custom_patterns = settings.get("mcp_log_mask_custom_patterns", "")
    if custom_patterns:
        for pattern in custom_patterns.strip().split("\n"):
            pattern = pattern.strip()
            if pattern:
                try:
                    masked = re.sub(pattern, MASK_REPLACEMENT, masked)
                except re.error as e:
                    logger.warning(f"Invalid custom masking pattern '{pattern}': {e}")

    return masked


def truncate_body(text: str, max_size: int) -> str:
    """Truncate body if it exceeds max size"""
    if not text:
        return text

    if len(text) > max_size:
        return text[:max_size] + "\n[TRUNCATED]"

    return text


def _write_log_entry(app: Flask, log_data: dict[str, Any]):
    """Write log entry to database (runs in background thread)"""
    try:
        with app.app_context():
            from app.models.models import McpConnectionLog, db

            log_entry = McpConnectionLog(
                created_at=log_data.get("created_at", datetime.now(timezone.utc).replace(tzinfo=None)),
                duration_ms=log_data.get("duration_ms"),
                account_id=log_data.get("account_id"),
                account_name=log_data.get("account_name"),
                mcp_service_id=log_data.get("mcp_service_id"),
                mcp_service_name=log_data.get("mcp_service_name"),
                app_id=log_data.get("app_id"),
                app_name=log_data.get("app_name"),
                capability_id=log_data.get("capability_id"),
                capability_name=log_data.get("capability_name"),
                mcp_method=log_data.get("mcp_method") or "unknown",
                tool_name=log_data.get("tool_name"),
                request_id=log_data.get("request_id"),
                request_body=log_data.get("request_body"),
                response_body=log_data.get("response_body"),
                status_code=log_data.get("status_code"),
                is_success=log_data.get("is_success", True),
                error_code=log_data.get("error_code"),
                error_message=log_data.get("error_message"),
                ip_address=log_data.get("ip_address"),
                user_agent=log_data.get("user_agent"),
                access_control=log_data.get("access_control"),
            )

            db.session.add(log_entry)
            db.session.commit()
            logger.debug(f"MCP connection log written: {log_data.get('mcp_method')} from {log_data.get('ip_address')}")

    except Exception as e:
        logger.error(f"Failed to write MCP connection log: {e}")


def _log_to_stdout(log_data: dict[str, Any]):
    """
    Output structured JSON log to stdout for container log aggregation.

    This enables automatic log collection by:
    - AWS ECS/Fargate → CloudWatch Logs
    - Google Cloud Run → Cloud Logging
    - Azure Container Apps → Azure Monitor
    - Kubernetes → kubelet → logging backend
    - Any Docker-based platform

    Args:
        log_data: Log data dictionary (already masked and truncated)
    """
    try:
        # Build structured log entry
        created_at = log_data.get("created_at")
        timestamp = (
            created_at.isoformat() + "Z" if created_at is not None else datetime.now(timezone.utc).isoformat() + "Z"
        )
        log_entry = {
            "timestamp": timestamp,
            "log_type": "mcp_connection",
            "level": "ERROR" if not log_data.get("is_success", True) else "INFO",
            "mcp_method": log_data.get("mcp_method"),
            "mcp_service_id": log_data.get("mcp_service_id"),
            "mcp_service_name": log_data.get("mcp_service_name"),
            "app_id": log_data.get("app_id"),
            "app_name": log_data.get("app_name"),
            "capability_id": log_data.get("capability_id"),
            "capability_name": log_data.get("capability_name"),
            "tool_name": log_data.get("tool_name"),
            "account_id": log_data.get("account_id"),
            "account_name": log_data.get("account_name"),
            "status_code": log_data.get("status_code"),
            "is_success": log_data.get("is_success", True),
            "duration_ms": log_data.get("duration_ms"),
            "ip_address": log_data.get("ip_address"),
            "user_agent": log_data.get("user_agent"),
            "access_control": log_data.get("access_control"),
            "request_id": log_data.get("request_id"),
            "error_code": log_data.get("error_code"),
            "error_message": log_data.get("error_message"),
            "request_body": log_data.get("request_body"),
            "response_body": log_data.get("response_body"),
        }

        # Output as single-line JSON (required for proper log aggregation)
        print(json.dumps(log_entry, ensure_ascii=False), file=sys.stdout, flush=True)

    except Exception as e:
        # Errors in stdout logging should not affect application
        print(
            json.dumps(
                {
                    "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
                    "log_type": "mcp_logger_error",
                    "level": "ERROR",
                    "error": str(e),
                    "message": "Failed to output structured log to stdout",
                },
                ensure_ascii=False,
            ),
            file=sys.stderr,
            flush=True,
        )


def log_mcp_request(
    app: Flask,
    context: LogContext,
    response_body: str | None = None,
    status_code: int = 200,
    is_success: bool = True,
    error_code: int | None = None,
    error_message: str | None = None,
):
    """
    Log an MCP request asynchronously.

    Args:
        app: Flask application instance
        context: LogContext with request metadata
        response_body: Response body (will be masked and truncated)
        status_code: HTTP-like status code
        is_success: Whether the request was successful
        error_code: JSON-RPC error code if any
        error_message: Error message if any
    """
    try:
        # Get settings
        settings = get_log_settings(app)

        # Check if logging is enabled
        if not settings.get("mcp_log_enabled", True):
            return

        max_body_size = settings.get("mcp_log_max_body_size", 10240)

        # Prepare request body (mask and truncate)
        masked_request = None
        if context.request_body:
            masked_request = mask_sensitive_data(context.request_body, settings)
            masked_request = truncate_body(masked_request, max_body_size)

        # Prepare response body (mask and truncate)
        masked_response = None
        if response_body:
            masked_response = mask_sensitive_data(response_body, settings)
            masked_response = truncate_body(masked_response, max_body_size)

        # Build log data
        log_data = {
            "created_at": datetime.now(timezone.utc).replace(tzinfo=None),
            "duration_ms": context.get_duration_ms(),
            "account_id": context.account_id,
            "account_name": context.account_name,
            "mcp_service_id": context.mcp_service_id,
            "mcp_service_name": context.mcp_service_name,
            "app_id": context.app_id,
            "app_name": context.app_name,
            "capability_id": context.capability_id,
            "capability_name": context.capability_name,
            "mcp_method": context.mcp_method,
            "tool_name": context.tool_name,
            "request_id": context.request_id,
            "request_body": masked_request,
            "response_body": masked_response,
            "status_code": status_code,
            "is_success": is_success,
            "error_code": error_code,
            "error_message": error_message,
            "ip_address": context.ip_address,
            "user_agent": context.user_agent,
            "access_control": context.access_control,
        }

        # Output to stdout (synchronous, immediate)
        if STDOUT_LOGGING_ENABLED:
            _log_to_stdout(log_data)

        # Async DB write in production; synchronous under test like the other log writers, because
        # a background thread sharing the in-memory SQLite connection can crash the interpreter
        if app.config.get("TESTING"):
            _write_log_entry(app, log_data)
        else:
            _executor.submit(_write_log_entry, app, log_data)

    except Exception as e:
        logger.error(f"Failed to queue MCP connection log: {e}")


def create_log_context_from_request(request) -> LogContext:
    """Create a LogContext from a Flask request object"""
    context = LogContext()
    context.start()

    # Extract client info
    # Trusted X-Forwarded-For hops are already applied to remote_addr by ProxyFix
    context.ip_address = request.remote_addr

    context.user_agent = request.headers.get("User-Agent", "")[:500]  # Limit length

    return context


def shutdown_logger():
    """Shutdown the thread pool executor gracefully"""
    _executor.shutdown(wait=True)
