"""
Tests for multi-admin-account support:

- AdminCredentials model (unique username constraint)
- Multi-admin login via /login
- Per-user forced credential change redirect (login_required)
- Self-service credential change via /api/admin/credentials
- Admin account management API: /api/admin-users, /api/admin-users/<id>
"""

import pytest

from app.models.models import AdminCredentials


@pytest.fixture
def admin_initialized(db):
    """An admin account that has already completed its first-login credential change."""
    cred = AdminCredentials(username="alice", is_initialized=True)
    cred.set_password("alice-password-1")
    db.session.add(cred)
    db.session.commit()
    return cred


@pytest.fixture
def admin_pending(db):
    """An admin account still pending its forced first-login credential change."""
    cred = AdminCredentials(username="bootstrap_admin", is_initialized=False)
    cred.set_password("bootstrap-pass-1")
    db.session.add(cred)
    db.session.commit()
    return cred


def _login(client, username, password):
    return client.post("/login", json={"username": username, "password": password})


# ---------------------------------------------------------------------------
# AdminCredentials model
# ---------------------------------------------------------------------------


class TestAdminCredentialsModel:
    def test_set_password_and_check_password(self, db):
        cred = AdminCredentials(username="model_user")
        cred.set_password("super-secret-1")
        db.session.add(cred)
        db.session.commit()

        assert cred.check_password("super-secret-1") is True
        assert cred.check_password("wrong-password") is False

    def test_username_unique_constraint(self, db):
        cred1 = AdminCredentials(username="dup_user")
        cred1.set_password("password-one")
        db.session.add(cred1)
        db.session.commit()

        cred2 = AdminCredentials(username="dup_user")
        cred2.set_password("password-two")
        db.session.add(cred2)

        from sqlalchemy.exc import IntegrityError

        with pytest.raises(IntegrityError):
            db.session.commit()

    def test_to_dict_excludes_password_hash(self, db, admin_initialized):
        data = admin_initialized.to_dict()
        assert "password_hash" not in data
        assert data["username"] == "alice"
        assert data["is_initialized"] is True


# ---------------------------------------------------------------------------
# Multi-admin login
# ---------------------------------------------------------------------------


class TestMultiAdminLogin:
    def test_login_with_existing_admin(self, client, db, admin_initialized):
        resp = _login(client, "alice", "alice-password-1")
        assert resp.status_code == 200
        assert resp.get_json()["success"] is True

    def test_login_with_second_admin_alongside_first(self, client, db, admin_initialized, admin_pending):
        """Two separate admin accounts can both authenticate independently."""
        resp1 = _login(client, "alice", "alice-password-1")
        assert resp1.status_code == 200

        client2 = client.application.test_client()
        resp2 = _login(client2, "bootstrap_admin", "bootstrap-pass-1")
        assert resp2.status_code == 200

    def test_login_wrong_password_for_existing_username(self, client, db, admin_initialized):
        resp = _login(client, "alice", "wrong-password")
        assert resp.status_code == 401

    def test_login_unknown_username_when_other_admins_exist(self, client, db, admin_initialized):
        """When admin rows exist, an unknown username must not fall back to env credentials."""
        resp = _login(client, "no_such_admin", "anything")
        assert resp.status_code == 401

    def test_bootstrap_env_fallback_when_table_empty(self, client, db):
        """With zero AdminCredentials rows, login falls back to env-configured credentials."""
        assert AdminCredentials.query.count() == 0
        resp = _login(client, "admin", "admin")
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Per-user forced credential change (login_required)
# ---------------------------------------------------------------------------


class TestPerUserForcedCredentialChange:
    def test_pending_admin_redirected_to_change_credentials(self, client, db, admin_pending):
        _login(client, "bootstrap_admin", "bootstrap-pass-1")
        resp = client.get("/dashboard")
        assert resp.status_code == 302
        assert "/change-credentials" in resp.headers["Location"]

    def test_initialized_admin_not_redirected(self, client, db, admin_initialized):
        _login(client, "alice", "alice-password-1")
        resp = client.get("/dashboard")
        assert resp.status_code == 200

    def test_one_pending_admin_does_not_block_other_initialized_admin(self, app, db, admin_initialized, admin_pending):
        """Regression check: the forced-change flag must be evaluated per logged-in user,
        not against an arbitrary AdminCredentials row in the table."""
        pending_client = app.test_client()
        _login(pending_client, "bootstrap_admin", "bootstrap-pass-1")
        assert pending_client.get("/dashboard").status_code == 302

        initialized_client = app.test_client()
        _login(initialized_client, "alice", "alice-password-1")
        assert initialized_client.get("/dashboard").status_code == 200


# ---------------------------------------------------------------------------
# Self-service credential change: POST /api/admin/credentials
# ---------------------------------------------------------------------------


class TestSelfServiceCredentialChange:
    def test_requires_login(self, client, db, admin_initialized):
        resp = client.post("/api/admin/credentials", json={"password": "new-password-1"})
        assert resp.status_code in (302, 401)

    def test_updates_own_password(self, client, db, admin_initialized):
        _login(client, "alice", "alice-password-1")
        resp = client.post("/api/admin/credentials", json={"password": "brand-new-pass-1"})
        assert resp.status_code == 200

        db.session.refresh(admin_initialized)
        assert admin_initialized.check_password("brand-new-pass-1") is True

    def test_updates_own_username_and_syncs_session(self, client, db, admin_initialized):
        _login(client, "alice", "alice-password-1")
        resp = client.post("/api/admin/credentials", json={"username": "alice_renamed"})
        assert resp.status_code == 200

        # Session should now recognize the new username for subsequent requests
        resp2 = client.get("/dashboard")
        assert resp2.status_code == 200

        # Old username can no longer log in; new username can
        resp3 = _login(client.application.test_client(), "alice", "alice-password-1")
        assert resp3.status_code == 401
        resp4 = _login(client.application.test_client(), "alice_renamed", "alice-password-1")
        assert resp4.status_code == 200

    def test_rejects_username_already_used_by_another_admin(self, client, db, admin_initialized, admin_pending):
        _login(client, "alice", "alice-password-1")
        resp = client.post("/api/admin/credentials", json={"username": "bootstrap_admin"})
        assert resp.status_code == 409

    def test_only_changes_logged_in_users_own_account(self, client, db, admin_initialized, admin_pending):
        """Changing credentials while logged in as 'alice' must not affect 'bootstrap_admin'."""
        _login(client, "alice", "alice-password-1")
        client.post("/api/admin/credentials", json={"password": "alice-new-pass-1"})

        db.session.refresh(admin_pending)
        assert admin_pending.check_password("bootstrap-pass-1") is True
        assert admin_pending.is_initialized is False

    def test_marks_initialized_after_change(self, client, db, admin_pending):
        _login(client, "bootstrap_admin", "bootstrap-pass-1")
        client.post("/api/admin/credentials", json={"password": "after-change-pass-1"})

        db.session.refresh(admin_pending)
        assert admin_pending.is_initialized is True


# ---------------------------------------------------------------------------
# Admin account management API: /api/admin-users
# ---------------------------------------------------------------------------


class TestAdminUsersListAndCreate:
    def test_list_requires_login(self, client, db, admin_initialized):
        resp = client.get("/api/admin-users")
        assert resp.status_code in (302, 401)

    def test_list_returns_all_admin_accounts(self, auth_client, db, admin_initialized, admin_pending):
        resp = auth_client.get("/api/admin-users")
        assert resp.status_code == 200
        usernames = {u["username"] for u in resp.get_json()}
        assert usernames == {"alice", "bootstrap_admin"}

    def test_create_admin_user(self, auth_client, db):
        resp = auth_client.post("/api/admin-users", json={"username": "new_admin", "password": "new-admin-pass-1"})
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["username"] == "new_admin"
        # Created directly via the management screen: no forced first-login change
        assert data["is_initialized"] is True

    def test_create_admin_user_can_login_immediately(self, auth_client, db):
        auth_client.post("/api/admin-users", json={"username": "new_admin", "password": "new-admin-pass-1"})

        fresh_client = auth_client.application.test_client()
        resp = _login(fresh_client, "new_admin", "new-admin-pass-1")
        assert resp.status_code == 200
        # No forced redirect expected for a directly-created admin
        assert resp.get_json().get("change_required") is not True

    def test_create_rejects_duplicate_username(self, auth_client, db, admin_initialized):
        resp = auth_client.post("/api/admin-users", json={"username": "alice", "password": "whatever-1"})
        assert resp.status_code == 409

    def test_create_rejects_short_password(self, auth_client, db):
        resp = auth_client.post("/api/admin-users", json={"username": "short_pw", "password": "short"})
        assert resp.status_code == 400

    def test_create_rejects_missing_username(self, auth_client, db):
        resp = auth_client.post("/api/admin-users", json={"password": "valid-password-1"})
        assert resp.status_code == 400


class TestAdminUserDetailUpdateDelete:
    def test_get_detail(self, auth_client, db, admin_initialized):
        resp = auth_client.get(f"/api/admin-users/{admin_initialized.id}")
        assert resp.status_code == 200
        assert resp.get_json()["username"] == "alice"

    def test_get_detail_404_for_unknown_id(self, auth_client, db):
        resp = auth_client.get("/api/admin-users/999999")
        assert resp.status_code == 404

    def test_update_username(self, auth_client, db, admin_initialized):
        resp = auth_client.put(f"/api/admin-users/{admin_initialized.id}", json={"username": "alice2"})
        assert resp.status_code == 200
        assert resp.get_json()["username"] == "alice2"

    def test_update_rejects_duplicate_username(self, auth_client, db, admin_initialized, admin_pending):
        resp = auth_client.put(f"/api/admin-users/{admin_pending.id}", json={"username": "alice"})
        assert resp.status_code == 409

    def test_update_password(self, auth_client, db, admin_initialized):
        resp = auth_client.put(f"/api/admin-users/{admin_initialized.id}", json={"password": "updated-pass-1"})
        assert resp.status_code == 200

        db.session.refresh(admin_initialized)
        assert admin_initialized.check_password("updated-pass-1") is True

    def test_update_rejects_short_password(self, auth_client, db, admin_initialized):
        resp = auth_client.put(f"/api/admin-users/{admin_initialized.id}", json={"password": "short"})
        assert resp.status_code == 400

    def test_delete_succeeds_when_multiple_admins_exist(self, auth_client, db, admin_initialized, admin_pending):
        resp = auth_client.delete(f"/api/admin-users/{admin_pending.id}")
        assert resp.status_code == 204
        assert AdminCredentials.query.count() == 1

    def test_delete_last_remaining_admin_is_forbidden(self, auth_client, db, admin_initialized):
        assert AdminCredentials.query.count() == 1
        resp = auth_client.delete(f"/api/admin-users/{admin_initialized.id}")
        assert resp.status_code == 400
        assert AdminCredentials.query.count() == 1

    def test_cannot_delete_own_logged_in_account(self, client, db, admin_initialized, admin_pending):
        _login(client, "alice", "alice-password-1")
        resp = client.delete(f"/api/admin-users/{admin_initialized.id}")
        assert resp.status_code == 400
        assert AdminCredentials.query.count() == 2

    def test_can_delete_other_account_while_logged_in(self, client, db, admin_initialized, admin_pending):
        _login(client, "alice", "alice-password-1")
        resp = client.delete(f"/api/admin-users/{admin_pending.id}")
        assert resp.status_code == 204
        assert AdminCredentials.query.count() == 1

    def test_renaming_own_account_via_management_api_syncs_session(self, client, db, admin_initialized, admin_pending):
        _login(client, "alice", "alice-password-1")
        resp = client.put(f"/api/admin-users/{admin_initialized.id}", json={"username": "alice_v2"})
        assert resp.status_code == 200

        # Session must still be recognized after the rename
        resp2 = client.get("/dashboard")
        assert resp2.status_code == 200

    def test_renaming_another_account_does_not_affect_own_session(self, client, db, admin_initialized, admin_pending):
        _login(client, "alice", "alice-password-1")
        client.put(f"/api/admin-users/{admin_pending.id}", json={"username": "bootstrap_admin_v2"})

        resp = client.get("/dashboard")
        assert resp.status_code == 200
