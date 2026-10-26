"""
Authentication Controller
Handles admin login, logout, and authentication with brute-force protection
"""

import logging
from datetime import datetime, timedelta, timezone
from functools import wraps

from flask import Blueprint, current_app, jsonify, redirect, render_template, request, session, url_for

from app.services.background import BoundedExecutor

auth_bp = Blueprint("auth", __name__)
logger = logging.getLogger(__name__)

# Thread pool for async log writing
_executor = BoundedExecutor(max_workers=2, max_pending=1000, name="login-log")

# APIs the change-credentials page needs before the forced credential change completes
_CREDENTIAL_CHANGE_APIS = frozenset({"/api/admin/credentials", "/api/settings/language"})


_UNSAFE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})


def reject_cross_origin_request():
    """CSRF protection for cookie-authenticated routes (before_request hook).

    Browsers attach Origin (or at least Referer) to cross-origin state-changing
    requests, so a mismatch with our own host means the request came from another
    site. Requests carrying neither header are not from a browser and are allowed.
    """
    from urllib.parse import urlsplit

    if request.method not in _UNSAFE_METHODS:
        return None

    source = request.headers.get("Origin") or request.headers.get("Referer")
    if source is None:
        return None
    # Ports are ignored: a reverse proxy may drop them from Host, and cookies are not port-scoped anyway.
    # "null" (opaque origin) has no hostname and is rejected as well.
    if urlsplit(source).hostname != urlsplit(f"//{request.host}").hostname:
        logger.warning("Rejected cross-origin %s %s", request.method, request.path)
        if request.path.startswith("/api/"):
            return jsonify({"error": "Cross-origin request rejected"}), 403
        return "Cross-origin request rejected", 403
    return None


def login_required(f):
    """Decorator to require admin login.

    After login succeeds, if the currently logged-in admin's credentials have
    not yet been changed from their initial values (is_initialized=False) they
    are redirected to the credential change page for every request until they
    complete the change. Only the bootstrap admin (created from env vars) ever
    starts with is_initialized=False; admins created via the admin accounts
    management screen are initialized immediately.
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("admin_logged_in"):
            return redirect(url_for("auth.login"))

        # Check whether the admin has completed the forced credential change.
        # Allow /admin/change-credentials itself so there is no redirect loop, and
        # only the APIs that page calls; other APIs get a JSON 403 instead of a redirect.
        from flask import request as _req

        change_url = url_for("admin.change_credentials")
        if not _req.path.startswith(change_url) and _req.path not in _CREDENTIAL_CHANGE_APIS:
            cred = _get_current_admin_credentials()
            if cred is not None and not cred.is_initialized:
                if _req.path.startswith("/api/"):
                    return jsonify({"error": "Credential change required"}), 403
                return redirect(change_url)

        return f(*args, **kwargs)

    return decorated_function


def _get_admin_credentials_by_username(username):
    """Return the AdminCredentials row matching username, or None if not found."""
    try:
        from app.models.models import AdminCredentials

        return AdminCredentials.query.filter_by(username=username).first()
    except Exception:
        return None


def _get_current_admin_credentials():
    """Return the AdminCredentials row for the currently logged-in admin (by session), or None."""
    username = session.get("admin_username")
    if not username:
        return None
    return _get_admin_credentials_by_username(username)


@auth_bp.route("/")
def index():
    """Root route - redirect to dashboard or login"""
    if session.get("admin_logged_in"):
        return redirect(url_for("admin.dashboard"))
    return redirect(url_for("auth.login"))


def _get_client_ip():
    """Get client IP address from request.

    X-Forwarded-For is resolved by ProxyFix only for the configured number of trusted
    proxies (TRUSTED_PROXY_COUNT), so a client cannot spoof its address with the header.
    """
    return request.remote_addr or "0.0.0.0"


def _get_lock_settings():
    """Get login lock settings from AdminSettings"""
    from app.models.models import AdminSettings

    max_attempts = AdminSettings.query.filter_by(setting_key="login_max_attempts").first()
    lock_duration = AdminSettings.query.filter_by(setting_key="login_lock_duration_minutes").first()

    return {
        "max_attempts": int(max_attempts.setting_value) if max_attempts else 5,
        "lock_duration_minutes": int(lock_duration.setting_value) if lock_duration else 30,
    }


def _check_lock_status(ip_address):
    """Check if IP is currently locked (without incrementing counter)"""
    from app.models.models import LoginLockStatus

    _get_lock_settings()
    lock_status = LoginLockStatus.query.filter_by(ip_address=ip_address).first()

    if lock_status and lock_status.is_locked():
        remaining_minutes = int(
            (lock_status.locked_until - datetime.now(timezone.utc).replace(tzinfo=None)).total_seconds() / 60
        )
        return True, f"アカウントがロックされています。残り約{remaining_minutes}分後に解除されます。"

    return False, None


def _check_and_update_lock_status(ip_address, is_success=False):
    """Check if IP is locked and update lock status"""
    from app.models.models import LoginLockStatus, db

    settings = _get_lock_settings()
    lock_status = LoginLockStatus.query.filter_by(ip_address=ip_address).first()

    if lock_status:
        # Check if currently locked
        if lock_status.is_locked():
            remaining_minutes = int(
                (lock_status.locked_until - datetime.now(timezone.utc).replace(tzinfo=None)).total_seconds() / 60
            )
            return True, f"アカウントがロックされています。残り約{remaining_minutes}分後に解除されます。"

        # If lock period has expired, reset the counter
        if lock_status.locked_until and lock_status.locked_until < datetime.now(timezone.utc).replace(tzinfo=None):
            lock_status.failed_attempts = 0
            lock_status.locked_until = None

        if is_success:
            # Reset on successful login
            lock_status.failed_attempts = 0
            lock_status.locked_until = None
        else:
            # Increment failed attempts
            lock_status.failed_attempts += 1
            lock_status.last_attempt_at = datetime.now(timezone.utc).replace(tzinfo=None)

            # Lock if threshold exceeded
            if lock_status.failed_attempts >= settings["max_attempts"]:
                lock_status.locked_until = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(
                    minutes=settings["lock_duration_minutes"]
                )
                db.session.commit()
                return (
                    True,
                    f"ログイン試行回数が上限に達しました。{settings['lock_duration_minutes']}分間ロックされます。",
                )

        lock_status.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        db.session.commit()
    else:
        # Create new lock status record
        if not is_success:
            lock_status = LoginLockStatus(
                ip_address=ip_address,
                failed_attempts=1,
                last_attempt_at=datetime.now(timezone.utc).replace(tzinfo=None),
            )
            db.session.add(lock_status)
            db.session.commit()

    return False, None


def _log_login_attempt(username, ip_address, user_agent, is_success, failure_reason=None, session_id=None):
    """Log login attempt asynchronously (or synchronously in test mode)"""
    import os

    # Captured here because the worker thread has no application context of its own
    app = current_app._get_current_object()

    def _write_log():
        try:
            from app.models.models import AdminLoginLog, db

            with app.app_context():
                log_entry = AdminLoginLog(
                    created_at=datetime.now(timezone.utc).replace(tzinfo=None),
                    username=username,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    is_success=is_success,
                    failure_reason=failure_reason,
                    session_id=session_id,
                )
                db.session.add(log_entry)
                db.session.commit()
                logger.debug(
                    f"Login attempt logged: {username} from {ip_address} - {'Success' if is_success else 'Failure'}"
                )
        except Exception as e:
            logger.error(f"Failed to log login attempt: {e}")

    # In test mode, execute synchronously
    if os.environ.get("TESTING") or app.config.get("TESTING"):
        _write_log()
    else:
        _executor.submit(_write_log)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """Login page and handler with brute-force protection"""
    if request.method == "POST":
        data = request.get_json() if request.is_json else request.form
        username = data.get("username", "")
        password = data.get("password", "")

        ip_address = _get_client_ip()
        user_agent = request.headers.get("User-Agent", "")[:500]

        # Check if IP is locked (without incrementing counter)
        is_locked, lock_message = _check_lock_status(ip_address)
        if is_locked:
            _log_login_attempt(username, ip_address, user_agent, False, "account_locked")
            if request.is_json:
                return jsonify({"success": False, "message": lock_message}), 429
            return render_template("login.html", error=lock_message)

        # Validate credentials — look up by username across all admin accounts,
        # falling back to env-based config only when no admin account exists yet
        # (bootstrap edge case before the first seed has run).
        from app.models.models import AdminCredentials

        cred = _get_admin_credentials_by_username(username)
        authenticated = False
        if cred is not None:
            authenticated = cred.check_password(password)
        elif AdminCredentials.query.count() == 0:
            authenticated = username == current_app.config.get(
                "ADMIN_USERNAME", ""
            ) and password == current_app.config.get("ADMIN_PASSWORD", "")

        if authenticated:
            # Success - clear lock status
            _check_and_update_lock_status(ip_address, is_success=True)

            session.clear()
            session.permanent = True
            session["admin_logged_in"] = True
            session["admin_username"] = username

            # Log successful login
            _log_login_attempt(
                username, ip_address, user_agent, True, session_id=session.sid if hasattr(session, "sid") else None
            )

            # Force credential change on first login
            if cred is not None and not cred.is_initialized:
                change_url = url_for("admin.change_credentials")
                if request.is_json:
                    return jsonify({"success": True, "redirect": change_url, "change_required": True})
                return redirect(change_url)

            if request.is_json:
                return jsonify({"success": True, "message": "ログインしました"})
            return redirect(url_for("admin.dashboard"))

        # Login failed - determine reason
        if cred is not None:
            # Found an account with this username, so the password was wrong
            failure_reason = "invalid_password"
        elif AdminCredentials.query.count() == 0:
            failure_reason = (
                "invalid_username" if username != current_app.config.get("ADMIN_USERNAME", "") else "invalid_password"
            )
        else:
            failure_reason = "invalid_username"

        # Update lock status (increment failed attempts)
        _check_and_update_lock_status(ip_address, is_success=False)

        # Log failed login
        _log_login_attempt(username, ip_address, user_agent, False, failure_reason)

        error_msg = "ユーザー名またはパスワードが正しくありません"
        if request.is_json:
            return jsonify({"success": False, "message": error_msg}), 401
        return render_template("login.html", error=error_msg)

    return render_template("login.html")


@auth_bp.route("/logout")
def logout():
    """Logout handler"""
    session.clear()
    return redirect(url_for("auth.login"))
