"""
Regression tests for the asynchronous (production) path of the log writers.

Unit tests normally write logs synchronously; these tests force the background
thread path, which previously failed with "Working outside of application context".
"""

import threading

import pytest

from app.controllers import auth_controller
from app.models.models import AdminActionLog, AdminLoginLog
from app.services import audit_logger
from app.services.background import BoundedExecutor


@pytest.fixture
def async_mode(app, monkeypatch):
    monkeypatch.delenv("TESTING", raising=False)
    monkeypatch.setitem(app.config, "TESTING", False)


def test_login_attempt_is_written_from_background_thread(app, db, async_mode, monkeypatch):
    executor = BoundedExecutor(max_workers=1, max_pending=10, name="test-login-log")
    monkeypatch.setattr(auth_controller, "_executor", executor)

    with app.test_request_context("/login"):
        auth_controller._log_login_attempt("someone", "10.0.0.1", "ua", False, "invalid_credentials")
    executor.shutdown(wait=True)

    assert AdminLoginLog.query.filter_by(username="someone").count() == 1


def test_admin_action_is_written_from_background_thread(app, db, async_mode, monkeypatch):
    executor = BoundedExecutor(max_workers=1, max_pending=10, name="test-audit-log")
    monkeypatch.setattr(audit_logger, "_executor", executor)

    with app.test_request_context("/api/apps"):
        audit_logger._log_admin_action("admin", "create", "app", 1, "App")
    executor.shutdown(wait=True)

    assert AdminActionLog.query.filter_by(resource_name="App").count() == 1


def test_bounded_executor_drops_work_when_full():
    executor = BoundedExecutor(max_workers=1, max_pending=1, name="test-bounded")
    release = threading.Event()

    first = executor.submit(release.wait)
    second = executor.submit(lambda: None)
    release.set()
    executor.shutdown(wait=True)

    assert first is not None
    assert second is None
