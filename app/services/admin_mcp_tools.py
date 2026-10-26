"""
Admin MCP Tools
Octopus MCP Proxy 自身を管理するための MCP ツール実装
"""

import logging
from datetime import datetime, timezone

from app.models.models import (
    AdminActionLog,
    McpConnectionLog,
    McpService,
    McpServiceTemplate,
    Service,
    Variable,
    db,
)

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


# ---------------------------------------------------------------------------
# 観測系ツール
# ---------------------------------------------------------------------------


def get_dashboard_summary() -> dict:
    """Octopus MCP Proxy の全体サマリーを返す"""
    mcp_service_count = McpService.query.count()
    enabled_mcp_service_count = McpService.query.filter_by(is_enabled=True).count()
    app_count = Service.query.count()
    variable_count = Variable.query.count()
    recent_errors = (
        McpConnectionLog.query.filter_by(is_success=False).order_by(McpConnectionLog.created_at.desc()).limit(5).all()
    )
    return {
        "mcp_service_count": mcp_service_count,
        "enabled_mcp_service_count": enabled_mcp_service_count,
        "app_count": app_count,
        "variable_count": variable_count,
        "recent_errors": [e.to_dict() for e in recent_errors],
    }


def get_connection_logs(limit: int = 50, offset: int = 0) -> dict:
    """MCP 接続ログを取得する"""
    limit = min(max(1, limit), 200)
    logs = McpConnectionLog.query.order_by(McpConnectionLog.created_at.desc()).offset(offset).limit(limit).all()
    total = McpConnectionLog.query.count()
    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "logs": [log.to_dict() for log in logs],
    }


def get_error_logs(limit: int = 50, offset: int = 0) -> dict:
    """エラーログのみ取得する"""
    limit = min(max(1, limit), 200)
    logs = (
        McpConnectionLog.query.filter_by(is_success=False)
        .order_by(McpConnectionLog.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    total = McpConnectionLog.query.filter_by(is_success=False).count()
    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "logs": [log.to_dict() for log in logs],
    }


def get_admin_action_logs(limit: int = 50, offset: int = 0) -> dict:
    """管理者操作ログを取得する"""
    limit = min(max(1, limit), 200)
    logs = AdminActionLog.query.order_by(AdminActionLog.created_at.desc()).offset(offset).limit(limit).all()
    total = AdminActionLog.query.count()
    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "logs": [log.to_dict() for log in logs],
    }


# ---------------------------------------------------------------------------
# MCP サービス管理ツール
# ---------------------------------------------------------------------------


def list_mcp_services() -> dict:
    """全 MCP サービス一覧を返す"""
    services = McpService.query.order_by(McpService.created_at.desc()).all()
    return {"mcp_services": [s.to_dict() for s in services]}


def create_mcp_service(
    name: str,
    identifier: str,
    routing_type: str = "path",
    description: str = "",
    access_control: str = "restricted",
) -> dict:
    """新しい MCP サービスを作成する"""
    if McpService.query.filter_by(identifier=identifier).first():
        return {"error": f"identifier '{identifier}' is already in use"}

    if routing_type not in ("subdomain", "path"):
        return {"error": "routing_type must be 'subdomain' or 'path'"}

    if access_control not in ("public", "restricted"):
        return {"error": "access_control must be 'public' or 'restricted'"}

    svc = McpService(
        name=name,
        identifier=identifier,
        routing_type=routing_type,
        description=description,
        access_control=access_control,
        is_enabled=True,
    )
    db.session.add(svc)
    db.session.commit()
    logger.info(f"Admin MCP: created McpService id={svc.id} name={svc.name}")
    return {"mcp_service": svc.to_dict()}


def delete_mcp_service(mcp_service_id: int) -> dict:
    """MCP サービスを削除する"""
    svc = db.session.get(McpService, mcp_service_id)
    if not svc:
        return {"error": f"MCP service id={mcp_service_id} not found"}
    db.session.delete(svc)
    db.session.commit()
    logger.info(f"Admin MCP: deleted McpService id={mcp_service_id}")
    return {"deleted": True, "id": mcp_service_id}


# ---------------------------------------------------------------------------
# アプリ (Service) 管理ツール
# ---------------------------------------------------------------------------


def list_apps(mcp_service_id: int | None = None) -> dict:
    """アプリ一覧を返す。mcp_service_id を指定すると絞り込み"""
    q = Service.query
    if mcp_service_id is not None:
        q = q.filter_by(mcp_service_id=mcp_service_id)
    apps = q.order_by(Service.created_at.desc()).all()
    return {"apps": [a.to_dict() for a in apps]}


# ---------------------------------------------------------------------------
# 変数管理ツール
# ---------------------------------------------------------------------------


def list_variables() -> dict:
    """変数一覧を返す（値はマスク）"""
    variables = Variable.query.order_by(Variable.name).all()
    return {"variables": [v.to_dict(include_value=False) for v in variables]}


def set_variable(name: str, value: str, description: str = "", is_secret: bool = True) -> dict:
    """変数を作成または更新する"""
    var = Variable.query.filter_by(name=name).first()
    if var:
        var.set_value(value)
        var.description = description
        var.is_secret = is_secret
    else:
        var = Variable(
            name=name,
            value_type="string",
            source_type="value",
            description=description,
            is_secret=is_secret,
        )
        var.set_value(value)
        db.session.add(var)
    db.session.commit()
    logger.info(f"Admin MCP: set variable name={name}")
    return {"variable": var.to_dict(include_value=False)}


def delete_variable(name: str) -> dict:
    """変数を削除する"""
    var = Variable.query.filter_by(name=name).first()
    if not var:
        return {"error": f"Variable '{name}' not found"}
    db.session.delete(var)
    db.session.commit()
    logger.info(f"Admin MCP: deleted variable name={name}")
    return {"deleted": True, "name": name}


# ---------------------------------------------------------------------------
# テンプレート管理ツール
# ---------------------------------------------------------------------------


def list_templates() -> dict:
    """テンプレート一覧を返す"""
    templates = McpServiceTemplate.query.order_by(McpServiceTemplate.name).all()
    return {"templates": [t.to_dict() for t in templates]}
