"""
Admin Controller
Handles admin panel routes (dashboard, services, accounts, capabilities)
"""

from flask import Blueprint, render_template

from app.controllers.auth_controller import login_required

admin_bp = Blueprint("admin", __name__)


@admin_bp.route("/dashboard")
@login_required
def dashboard():
    """Dashboard page"""
    return render_template("dashboard.html")


# ============= MCP Service Management Routes =============


@admin_bp.route("/mcp-services")
@login_required
def mcp_services_list():
    """MCP services list page"""
    return render_template("mcp_services/list.html")


@admin_bp.route("/mcp-services/new")
@login_required
def mcp_service_new():
    """New MCP service page"""
    return render_template("mcp_services/new.html")


@admin_bp.route("/mcp-services/<int:mcp_service_id>")
@login_required
def mcp_service_detail(mcp_service_id):
    """MCP service detail page"""
    return render_template("mcp_services/detail.html", mcp_service_id=mcp_service_id)


@admin_bp.route("/mcp-services/<int:mcp_service_id>/edit")
@login_required
def mcp_service_edit(mcp_service_id):
    """Edit MCP service page"""
    return render_template("mcp_services/edit.html", mcp_service_id=mcp_service_id)


# ============= Service Management Routes =============


@admin_bp.route("/mcp-services/<int:mcp_service_id>/apps")
@login_required
def services_list(mcp_service_id):
    """Services list page"""
    return render_template("services/list.html", mcp_service_id=mcp_service_id)


@admin_bp.route("/mcp-services/<int:mcp_service_id>/apps/new")
@login_required
def service_new(mcp_service_id):
    """New service page"""
    return render_template("services/new.html", mcp_service_id=mcp_service_id)


@admin_bp.route("/mcp-services/<int:mcp_service_id>/apps/<int:service_id>")
@login_required
def service_detail(mcp_service_id, service_id):
    """Service detail page"""
    return render_template("services/detail.html", mcp_service_id=mcp_service_id, service_id=service_id)


@admin_bp.route("/mcp-services/<int:mcp_service_id>/apps/<int:service_id>/edit")
@login_required
def service_edit(mcp_service_id, service_id):
    """Service edit page"""
    return render_template("services/edit.html", mcp_service_id=mcp_service_id, service_id=service_id)


@admin_bp.route("/mcp-services/<int:mcp_service_id>/apps/<int:service_id>/capabilities")
@login_required
def service_capabilities(mcp_service_id, service_id):
    """Service capabilities page"""
    return render_template("services/capabilities.html", mcp_service_id=mcp_service_id, service_id=service_id)


@admin_bp.route("/mcp-services/<int:mcp_service_id>/apps/<int:service_id>/capabilities/new")
@login_required
def capability_new(mcp_service_id, service_id):
    """New capability page"""
    return render_template("capabilities/new.html", mcp_service_id=mcp_service_id, service_id=service_id)


@admin_bp.route("/capabilities/<int:capability_id>")
@login_required
def capability_detail(capability_id):
    """Capability detail page"""
    return render_template("capabilities/detail.html", capability_id=capability_id)


@admin_bp.route("/capabilities/<int:capability_id>/edit")
@login_required
def capability_edit(capability_id):
    """Capability edit page"""
    return render_template("capabilities/edit.html", capability_id=capability_id)


# ============= Account Management Routes =============


@admin_bp.route("/accounts")
@login_required
def accounts_list():
    """Connection accounts list page"""
    return render_template("accounts/list.html")


@admin_bp.route("/accounts/new")
@login_required
def account_new():
    """New connection account page"""
    return render_template("accounts/new.html")


@admin_bp.route("/accounts/<int:account_id>")
@login_required
def account_detail(account_id):
    """Connection account detail page"""
    return render_template("accounts/detail.html", account_id=account_id)


# ============= Variables Management Routes =============


@admin_bp.route("/variables")
@login_required
def variables_list():
    """Variables list page"""
    return render_template("variables/list.html")


@admin_bp.route("/variables/new")
@login_required
def variable_new():
    """New variable page"""
    return render_template("variables/new.html")


@admin_bp.route("/variables/<int:variable_id>/edit")
@login_required
def variable_edit(variable_id):
    """Edit variable page"""
    return render_template("variables/edit.html", variable_id=variable_id)


# ============= Resources Management Routes =============


@admin_bp.route("/resources")
@login_required
def resources_list():
    """Resources list page"""
    return render_template("resources/list.html")


@admin_bp.route("/resources/new")
@login_required
def resource_new():
    """New resource page"""
    return render_template("resources/new.html")


@admin_bp.route("/resources/<int:resource_id>")
@login_required
def resource_detail(resource_id):
    """Resource detail page"""
    return render_template("resources/detail.html", resource_id=resource_id)


@admin_bp.route("/resources/<int:resource_id>/edit")
@login_required
def resource_edit(resource_id):
    """Edit resource page"""
    return render_template("resources/edit.html", resource_id=resource_id)


# ============= Template Management Routes =============


@admin_bp.route("/mcp-templates")
@login_required
def templates_list():
    """Templates list page (builtin and custom tabs)"""
    return render_template("mcp_templates/list.html")


@admin_bp.route("/mcp-templates/new")
@login_required
def template_new():
    """New custom template page"""
    return render_template("mcp_templates/new.html")


@admin_bp.route("/mcp-templates/<int:template_id>")
@login_required
def template_detail(template_id):
    """Template detail page"""
    return render_template("mcp_templates/detail.html", template_id=template_id)


@admin_bp.route("/mcp-templates/<int:template_id>/edit")
@login_required
def template_edit(template_id):
    """Template edit page"""
    return render_template("mcp_templates/edit.html", template_id=template_id)


@admin_bp.route("/mcp-templates/<int:template_id>/capabilities")
@login_required
def template_capabilities(template_id):
    """Template capabilities management page"""
    return render_template("mcp_templates/capabilities.html", template_id=template_id)


@admin_bp.route("/mcp-templates/<int:template_id>/capabilities/new")
@login_required
def template_capability_new(template_id):
    """New capability page"""
    return render_template("mcp_templates/capability_new.html", template_id=template_id)


@admin_bp.route("/mcp-templates/<int:template_id>/capabilities/<int:capability_id>")
@login_required
def template_capability_detail(template_id, capability_id):
    """Capability detail page"""
    return render_template("mcp_templates/capability_detail.html", template_id=template_id, capability_id=capability_id)


@admin_bp.route("/mcp-templates/<int:template_id>/capabilities/<int:capability_id>/edit")
@login_required
def template_capability_edit(template_id, capability_id):
    """Edit capability page"""
    return render_template("mcp_templates/capability_edit.html", template_id=template_id, capability_id=capability_id)


# ============= Connection Logs Management Routes =============


@admin_bp.route("/connection-logs")
@login_required
def connection_logs_index():
    """Connection logs index page - shows MCP services with log counts"""
    return render_template("connection_logs/index.html")


@admin_bp.route("/connection-logs/list")
@login_required
def connection_logs_list():
    """Connection logs list page for a specific MCP service"""
    return render_template("connection_logs/list.html")


@admin_bp.route("/connection-logs/<int:log_id>")
@login_required
def connection_log_detail(log_id):
    """Connection log detail page"""
    return render_template("connection_logs/detail.html", log_id=log_id)


@admin_bp.route("/connection-logs/settings")
@login_required
def connection_logs_settings():
    """Connection logs settings page"""
    return render_template("connection_logs/settings.html")


# ============= Credential Change Routes =============


@admin_bp.route("/change-credentials")
@login_required
def change_credentials():
    """Credential change page for the currently logged-in admin (forced on first login)."""
    from app.controllers.auth_controller import _get_current_admin_credentials
    from app.models.models import ConnectionAccount

    cred = _get_current_admin_credentials()
    system_account = ConnectionAccount.query.filter_by(is_system=True).first()

    return render_template(
        "change_credentials.html",
        cred=cred,
        system_account=system_account,
    )


# ============= Admin User (Web Login Accounts) Management Routes =============


@admin_bp.route("/admin-users")
@login_required
def admin_users_list():
    """Admin user (web UI login accounts) list page"""
    return render_template("admin_users/list.html")


@admin_bp.route("/admin-users/new")
@login_required
def admin_user_new():
    """New admin user registration page"""
    return render_template("admin_users/new.html")


@admin_bp.route("/admin-users/<int:user_id>")
@login_required
def admin_user_detail(user_id):
    """Admin user detail/edit page"""
    return render_template("admin_users/detail.html", user_id=user_id)


@admin_bp.route("/guide")
@login_required
def guide():
    """Connection guide page."""
    from app.controllers.admin_mcp_controller import ADMIN_TOOLS
    from app.models.models import ConnectionAccount

    system_account = ConnectionAccount.query.filter_by(is_system=True).first()

    return render_template(
        "guide.html",
        system_account=system_account,
        admin_tools=ADMIN_TOOLS,
    )
