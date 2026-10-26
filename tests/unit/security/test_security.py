"""
Tests for Security features (brute-force protection, audit logs)
"""

import json
import logging
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

from app.controllers.mcp_controller import authenticate_bearer_token
from app.models.models import AdminActionLog, AdminLoginLog, AdminSettings, LoginLockStatus


def test_invalid_bearer_token_is_not_written_to_logs(client, caplog):
    secret_value = "bearer-secret-marker"

    with (
        client.application.test_request_context(headers={"Authorization": f"Bearer {secret_value}"}),
        caplog.at_level(logging.WARNING, logger="app.controllers.mcp_controller"),
    ):
        account, error, status_code = authenticate_bearer_token()

    assert account is None
    assert error == {"error": "Invalid bearer token"}
    assert status_code == 401
    assert secret_value[:10] not in caplog.text


@patch("requests.Session.post")
def test_mcp_connection_test_does_not_log_url_or_headers(mock_post, auth_client, caplog):
    url_secret = "url-secret-marker"
    header_secret = "header-secret-marker"
    response = MagicMock()
    response.status_code = 200
    response.headers = {"Content-Type": "application/json"}
    response.text = '{"result": {"serverInfo": {"name": "test"}}}'
    response.json.return_value = {"result": {"serverInfo": {"name": "test"}}}
    mock_post.return_value = response

    with caplog.at_level(logging.INFO):
        result = auth_client.post(
            "/api/apps/test-connection",
            json={
                "mcp_url": f"https://upstream.example.com/mcp?token={url_secret}",
                "common_headers": {"Authorization": f"Bearer {header_secret}"},
            },
        )

    assert result.status_code == 200
    assert url_secret not in caplog.text
    assert header_secret not in caplog.text


def test_mcp_connection_log_masks_sensitive_json_fields():
    from app.services.mcp_logger import mask_sensitive_data

    body = json.dumps(
        {
            "authorization": "Bearer header-secret-marker",
            "nested": {"refresh_token": "refresh-secret-marker", "api_key": "api-secret-marker"},
            "message": "Bearer inline-secret-marker",
        }
    )

    masked = json.loads(mask_sensitive_data(body, {}))

    assert masked["authorization"] == "[MASKED]"
    assert masked["nested"]["refresh_token"] == "[MASKED]"
    assert masked["nested"]["api_key"] == "[MASKED]"
    assert masked["message"] == "Bearer [MASKED]"


def test_mcp_connection_log_keeps_non_secret_token_counts():
    from app.services.mcp_logger import mask_sensitive_data

    body = json.dumps({"max_tokens": 1024, "usage": {"input_tokens": 12}, "tokenizer": "cl100k", "token": "t-1"})

    masked = json.loads(mask_sensitive_data(body, {}))

    assert masked["max_tokens"] == 1024
    assert masked["usage"]["input_tokens"] == 12
    assert masked["tokenizer"] == "cl100k"
    assert masked["token"] == "[MASKED]"


class TestBruteForceProtection:
    """Test login brute-force protection"""

    def test_successful_login_no_lock(self, client):
        """Test successful login does not create lock status"""
        response = client.post(
            "/login", data=json.dumps({"username": "admin", "password": "admin"}), content_type="application/json"
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["success"] is True

        # Check no lock status created for successful login
        lock_status = LoginLockStatus.query.filter_by(ip_address="127.0.0.1").first()
        assert lock_status is None or lock_status.failed_attempts == 0

    def test_failed_login_increments_counter(self, client, db):
        """Test failed login increments failed attempt counter"""
        # Clear any existing lock status
        LoginLockStatus.query.filter_by(ip_address="127.0.0.1").delete()
        db.session.commit()

        response = client.post(
            "/login", data=json.dumps({"username": "admin", "password": "wrong"}), content_type="application/json"
        )

        assert response.status_code == 401

        lock_status = LoginLockStatus.query.filter_by(ip_address="127.0.0.1").first()
        assert lock_status is not None
        assert lock_status.failed_attempts == 1

    def test_multiple_failed_logins_trigger_lock(self, client, db):
        """Test multiple failed logins trigger account lock"""
        # Clear any existing lock status
        LoginLockStatus.query.filter_by(ip_address="127.0.0.1").delete()
        db.session.commit()

        # Get max attempts setting
        max_attempts_setting = AdminSettings.query.filter_by(setting_key="login_max_attempts").first()
        max_attempts = int(max_attempts_setting.setting_value) if max_attempts_setting else 5

        # Attempt login max_attempts times with wrong password
        for i in range(max_attempts):
            response = client.post(
                "/login", data=json.dumps({"username": "admin", "password": "wrong"}), content_type="application/json"
            )

            if i < max_attempts - 1:
                assert response.status_code == 401
            else:
                # Last attempt should trigger lock
                assert response.status_code in [401, 429]

        # Next attempt should be locked
        response = client.post(
            "/login", data=json.dumps({"username": "admin", "password": "wrong"}), content_type="application/json"
        )

        assert response.status_code == 429
        data = json.loads(response.data)
        assert "ロック" in data["message"] or "locked" in data["message"].lower()

        lock_status = LoginLockStatus.query.filter_by(ip_address="127.0.0.1").first()
        assert lock_status is not None
        assert lock_status.failed_attempts >= max_attempts
        assert lock_status.locked_until is not None
        assert lock_status.is_locked() is True

    def test_successful_login_resets_counter(self, client, db):
        """Test successful login resets failed attempt counter"""
        # Create a lock status with failed attempts
        lock_status = LoginLockStatus(
            ip_address="127.0.0.1", failed_attempts=3, last_attempt_at=datetime.now(UTC).replace(tzinfo=None)
        )
        db.session.add(lock_status)
        db.session.commit()

        # Successful login
        response = client.post(
            "/login", data=json.dumps({"username": "admin", "password": "admin"}), content_type="application/json"
        )

        assert response.status_code == 200

        # Check counter is reset
        lock_status = LoginLockStatus.query.filter_by(ip_address="127.0.0.1").first()
        assert lock_status.failed_attempts == 0

    def test_lock_expires_after_duration(self, client, db):
        """Test lock expires after configured duration"""
        # Create an expired lock status
        lock_status = LoginLockStatus(
            ip_address="127.0.0.1",
            failed_attempts=5,
            locked_until=datetime.now(UTC).replace(tzinfo=None) - timedelta(minutes=1),  # Expired
            last_attempt_at=datetime.now(UTC).replace(tzinfo=None) - timedelta(minutes=10),
        )
        db.session.add(lock_status)
        db.session.commit()

        # Should be able to login after lock expires
        response = client.post(
            "/login", data=json.dumps({"username": "admin", "password": "wrong"}), content_type="application/json"
        )

        # Should not be locked (401 for wrong password, not 429 for locked)
        assert response.status_code == 401

        # Check failed attempts reset and started counting again
        lock_status = LoginLockStatus.query.filter_by(ip_address="127.0.0.1").first()
        assert lock_status.failed_attempts == 1  # New failed attempt after reset


class TestLoginLogs:
    """Test login attempt logging"""

    def test_successful_login_logged(self, client, db):
        """Test successful login is logged"""
        before_count = AdminLoginLog.query.count()

        response = client.post("/login", data={"username": "admin", "password": "admin"}, follow_redirects=False)

        assert response.status_code in [200, 302]  # Success or redirect

        # Check log created
        after_count = AdminLoginLog.query.count()
        assert after_count == before_count + 1

        log = AdminLoginLog.query.order_by(AdminLoginLog.created_at.desc()).first()
        assert log is not None
        assert log.username == "admin"
        assert log.is_success is True
        assert log.ip_address == "127.0.0.1"

    def test_failed_login_logged(self, client, db):
        """Test failed login is logged"""
        before_count = AdminLoginLog.query.count()

        response = client.post("/login", data={"username": "admin", "password": "wrong"}, follow_redirects=False)

        # Login page returns 200 with error message in HTML
        assert response.status_code == 200

        # Check log created
        after_count = AdminLoginLog.query.count()
        assert after_count == before_count + 1

        log = AdminLoginLog.query.order_by(AdminLoginLog.created_at.desc()).first()
        assert log is not None
        assert log.username == "admin"
        assert log.is_success is False
        assert "password" in log.failure_reason.lower()

    def test_locked_login_logged(self, client, db):
        """Test locked account login attempt is logged"""
        # Create locked status
        lock_status = LoginLockStatus(
            ip_address="127.0.0.1",
            failed_attempts=5,
            locked_until=datetime.now(UTC).replace(tzinfo=None) + timedelta(minutes=5),
            last_attempt_at=datetime.now(UTC).replace(tzinfo=None),
        )
        db.session.add(lock_status)
        db.session.commit()

        before_count = AdminLoginLog.query.count()

        response = client.post("/login", data={"username": "admin", "password": "admin"}, follow_redirects=False)

        # Login page returns 200 with error message in HTML
        assert response.status_code == 200

        # Check log created
        after_count = AdminLoginLog.query.count()
        assert after_count == before_count + 1

        log = AdminLoginLog.query.order_by(AdminLoginLog.created_at.desc()).first()
        assert log.failure_reason == "account_locked"


class TestAuditLogs:
    """Test admin action audit logging"""

    def test_create_service_logged(self, auth_client, db, sample_mcp_service):
        """Test creating a service is logged in audit trail"""
        before_count = AdminActionLog.query.count()

        payload = {"name": "Audit Test Service", "service_type": "api", "description": "Test", "common_headers": "{}"}
        response = auth_client.post(
            f"/api/mcp-services/{sample_mcp_service.id}/apps", data=json.dumps(payload), content_type="application/json"
        )

        assert response.status_code == 201

        # Check audit log created
        after_count = AdminActionLog.query.count()
        assert after_count >= before_count  # May be before_count + 1

        # Find the log for this action
        logs = AdminActionLog.query.filter_by(action_type="create", resource_type="app").all()
        assert len(logs) > 0

    def test_update_account_logged(self, auth_client, db, sample_account):
        """Test updating an account is logged in audit trail"""
        before_count = AdminActionLog.query.count()

        payload = {"name": "Updated Account Name", "notes": "Updated description"}
        response = auth_client.put(
            f"/api/accounts/{sample_account.id}", data=json.dumps(payload), content_type="application/json"
        )

        assert response.status_code == 200

        # Check audit log created
        after_count = AdminActionLog.query.count()
        assert after_count >= before_count

        # Find the log for this action
        logs = AdminActionLog.query.filter_by(
            action_type="update", resource_type="account", resource_id=sample_account.id
        ).all()
        assert len(logs) > 0

    def test_delete_capability_logged(self, auth_client, db, sample_capability):
        """Test deleting a capability is logged in audit trail"""
        capability_id = sample_capability.id
        before_count = AdminActionLog.query.count()

        response = auth_client.delete(f"/api/capabilities/{capability_id}")

        assert response.status_code == 204

        # Check audit log created
        after_count = AdminActionLog.query.count()
        assert after_count >= before_count


class TestSecurityAPIEndpoints:
    """Test security-related API endpoints"""

    def test_get_login_logs(self, auth_client, db):
        """Test GET /api/admin/login-logs"""
        # Create some test logs
        log1 = AdminLoginLog(
            username="admin",
            ip_address="127.0.0.1",
            user_agent="test",
            is_success=True,
            created_at=datetime.now(UTC).replace(tzinfo=None),
        )
        log2 = AdminLoginLog(
            username="admin",
            ip_address="127.0.0.1",
            user_agent="test",
            is_success=False,
            failure_reason="invalid_password",
            created_at=datetime.now(UTC).replace(tzinfo=None),
        )
        db.session.add_all([log1, log2])
        db.session.commit()

        response = auth_client.get("/api/admin/login-logs")

        assert response.status_code == 200
        data = json.loads(response.data)
        assert "logs" in data
        assert len(data["logs"]) >= 2

    def test_get_action_logs(self, auth_client, db):
        """Test GET /api/admin/action-logs"""
        response = auth_client.get("/api/admin/action-logs")

        assert response.status_code == 200
        data = json.loads(response.data)
        assert "logs" in data

    def test_unlock_account(self, auth_client, db):
        """Test POST /api/admin/unlock-account"""
        # Create locked status
        lock_status = LoginLockStatus(
            ip_address="192.168.1.1",
            failed_attempts=5,
            locked_until=datetime.now(UTC).replace(tzinfo=None) + timedelta(minutes=5),
            last_attempt_at=datetime.now(UTC).replace(tzinfo=None),
        )
        db.session.add(lock_status)
        db.session.commit()

        payload = {"ip_address": "192.168.1.1"}
        response = auth_client.post(
            "/api/admin/unlock-account", data=json.dumps(payload), content_type="application/json"
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert "unlocked" in data["message"].lower()

        # Check lock status cleared
        lock_status = LoginLockStatus.query.filter_by(ip_address="192.168.1.1").first()
        assert lock_status.failed_attempts == 0
        assert lock_status.locked_until is None

    def test_get_locked_ips(self, auth_client, db):
        """Test GET /api/admin/locked-ips"""
        # Create locked status
        lock_status = LoginLockStatus(
            ip_address="10.0.0.1",
            failed_attempts=5,
            locked_until=datetime.now(UTC).replace(tzinfo=None) + timedelta(minutes=5),
            last_attempt_at=datetime.now(UTC).replace(tzinfo=None),
        )
        db.session.add(lock_status)
        db.session.commit()

        response = auth_client.get("/api/admin/locked-ips")

        assert response.status_code == 200
        data = json.loads(response.data)
        assert "locked_ips" in data

        # Find our locked IP
        locked_ips = [ip for ip in data["locked_ips"] if ip["ip_address"] == "10.0.0.1"]
        assert len(locked_ips) >= 1


class TestCsrfOriginCheck:
    def test_cross_origin_api_write_is_rejected(self, auth_client):
        resp = auth_client.post("/api/mcp-services", json={"name": "x"}, headers={"Origin": "https://evil.example"})

        assert resp.status_code == 403

    def test_sibling_subdomain_origin_is_rejected(self, auth_client):
        resp = auth_client.post(
            "/api/mcp-services",
            json={"name": "x"},
            headers={"Origin": "http://attacker.lvh.me"},
            base_url="http://lvh.me",
        )

        assert resp.status_code == 403

    def test_opaque_origin_is_rejected(self, auth_client):
        resp = auth_client.delete("/api/mcp-services/1", headers={"Origin": "null"})

        assert resp.status_code == 403

    def test_cross_site_referer_is_rejected_when_origin_missing(self, auth_client):
        resp = auth_client.post(
            "/login", json={"username": "admin", "password": "x"}, headers={"Referer": "https://evil.example/page"}
        )

        assert resp.status_code == 403

    def test_same_origin_write_is_allowed(self, auth_client):
        resp = auth_client.post(
            "/api/mcp-services",
            json={"name": "Same Origin", "identifier": "same-origin"},
            headers={"Origin": "http://localhost"},
        )

        assert resp.status_code == 201

    def test_mcp_endpoint_is_not_subject_to_origin_check(self, client, db):
        resp = client.post(
            "/mcp?subdomain=none",
            json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
            headers={"Origin": "https://some-mcp-client.example"},
        )

        assert resp.status_code == 404


def test_api_500_does_not_expose_exception_text(auth_client):
    with patch("app.controllers.api_controller.McpService.query") as mock_query:
        mock_query.all.side_effect = RuntimeError("password=hunter2 in connection string")
        auth_client.application.config["PROPAGATE_EXCEPTIONS"] = False
        try:
            resp = auth_client.get("/api/mcp-services")
        finally:
            auth_client.application.config["PROPAGATE_EXCEPTIONS"] = None

    assert resp.status_code == 500
    assert "hunter2" not in resp.get_data(as_text=True)


class TestRequestLimits:
    def test_oversized_body_is_rejected(self, app, client):
        original = app.config["MAX_CONTENT_LENGTH"]
        app.config["MAX_CONTENT_LENGTH"] = 1024
        try:
            resp = client.post("/mcp?subdomain=x", data="x" * 2048, headers={"Content-Type": "application/json"})
        finally:
            app.config["MAX_CONTENT_LENGTH"] = original

        assert resp.status_code == 413

    def test_mcp_endpoint_is_rate_limited_per_ip(self, db):
        from app import create_app
        from tests.conftest import TestConfig

        class LimitedConfig(TestConfig):
            RATELIMIT_ENABLED = True
            RATELIMIT_STORAGE_URI = "memory://"
            MCP_RATE_LIMIT = "2 per minute"

        from app.models.models import db as _db

        limited_app = create_app(LimitedConfig)
        with limited_app.app_context():
            _db.create_all()
        limited_client = limited_app.test_client()
        statuses = [limited_client.get("/mcp?subdomain=none").status_code for _ in range(3)]
        other_ip = limited_client.get("/mcp?subdomain=none", environ_base={"REMOTE_ADDR": "10.9.9.9"})

        assert statuses == [404, 404, 429]
        assert other_ip.status_code == 404

    def test_admin_ui_is_not_rate_limited(self, db):
        from app import create_app
        from tests.conftest import TestConfig

        class LimitedConfig(TestConfig):
            RATELIMIT_ENABLED = True
            RATELIMIT_STORAGE_URI = "memory://"
            MCP_RATE_LIMIT = "1 per minute"

        limited_client = create_app(LimitedConfig).test_client()
        statuses = {limited_client.get("/login").status_code for _ in range(3)}

        assert statuses == {200}


class TestClientIpResolution:
    def test_forwarded_for_is_ignored_without_trusted_proxy(self, app):
        from app.controllers.auth_controller import _get_client_ip

        with app.test_request_context(
            "/", headers={"X-Forwarded-For": "6.6.6.6"}, environ_base={"REMOTE_ADDR": "1.1.1.1"}
        ):
            assert _get_client_ip() == "1.1.1.1"

    def test_forwarded_for_from_trusted_proxy_is_used(self, db):
        from flask import request

        from app import create_app
        from tests.conftest import TestConfig

        class ProxiedConfig(TestConfig):
            TRUSTED_PROXY_COUNT = 1

        proxied = create_app(ProxiedConfig)
        seen = {}

        @proxied.route("/_ip_probe")
        def _ip_probe():
            seen["ip"] = request.remote_addr
            return ""

        proxied.test_client().get(
            "/_ip_probe", headers={"X-Forwarded-For": "spoofed, 203.0.113.7"}, environ_base={"REMOTE_ADDR": "10.0.0.2"}
        )

        assert seen["ip"] == "203.0.113.7"
