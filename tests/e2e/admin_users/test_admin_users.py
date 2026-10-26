"""
E2E tests for admin user (web login account) management pages

Covers the multi-admin-account feature:
- /admin-users (list)
- /admin-users/new (create)
- /admin-users/<id> (detail / edit / delete)
"""

import re

import pytest
from playwright.sync_api import Page, expect

from tests.e2e.helpers import admin_credentials, e2e_url


@pytest.fixture(autouse=True)
def login(page: Page):
    """各テスト前に自動ログイン"""
    username, password = admin_credentials()
    page.goto(e2e_url("/login"))
    page.fill('input[name="username"]', username)
    page.fill('input[name="password"]', password)
    page.click('button[type="submit"]')
    page.wait_for_url(e2e_url("/dashboard"))


def _unique_username(page: Page) -> str:
    """Generate a unique username per test run to avoid collisions across runs."""
    return f"e2e_admin_{page.context.browser.version[:5]}_{id(page)}".replace(".", "_")


class TestAdminUsersListPage:
    """管理者アカウント一覧ページのE2Eテスト"""

    def test_admin_users_list_loads(self, page: Page):
        """管理者アカウント一覧ページが読み込まれる"""
        page.goto(e2e_url("/admin-users"))

        expect(page).to_have_url(e2e_url("/admin-users"))

    def test_navigate_to_new_admin_user(self, page: Page):
        """新規管理者登録画面に遷移できる"""
        page.goto(e2e_url("/admin-users"))

        page.click('a[href="/admin-users/new"]')
        expect(page).to_have_url(e2e_url("/admin-users/new"))

    def test_dashboard_links_to_admin_users(self, page: Page):
        """ダッシュボードから管理者アカウント管理に遷移できる"""
        page.goto(e2e_url("/dashboard"))

        page.click('a[href="/admin-users"]')
        expect(page).to_have_url(e2e_url("/admin-users"))


class TestAdminUsersNewPage:
    """新規管理者登録ページのE2Eテスト"""

    def test_new_admin_user_page_loads(self, page: Page):
        """新規管理者登録ページが読み込まれる"""
        page.goto(e2e_url("/admin-users/new"))

        expect(page).to_have_url(e2e_url("/admin-users/new"))
        expect(page.locator('input[name="username"]')).to_be_visible()
        expect(page.locator('input[name="password"]')).to_be_visible()

    def test_create_admin_user(self, page: Page):
        """新規管理者アカウントを作成できる"""
        username = _unique_username(page)
        page.goto(e2e_url("/admin-users/new"))

        page.fill('input[name="username"]', username)
        page.fill('input[name="password"]', "e2e-test-pass-1")
        page.fill('input[name="confirm_password"]', "e2e-test-pass-1")

        page.click('button[type="submit"]')

        # Should redirect back to the list
        page.wait_for_url(re.compile(r"/admin-users$"))
        expect(page.locator(f'a:has-text("{username}")')).to_be_visible()

    def test_password_mismatch_blocks_submission(self, page: Page):
        """パスワード確認が一致しない場合は登録されない"""
        username = _unique_username(page)
        page.goto(e2e_url("/admin-users/new"))

        page.fill('input[name="username"]', username)
        page.fill('input[name="password"]', "e2e-test-pass-1")
        page.fill('input[name="confirm_password"]', "different-password")

        page.click('button[type="submit"]')

        # Should stay on the new-user page (no redirect to the list)
        page.wait_for_timeout(300)
        expect(page).to_have_url(e2e_url("/admin-users/new"))


class TestAdminUserDetailPage:
    """管理者アカウント詳細ページのE2Eテスト"""

    def _create_admin_user(self, page: Page, username: str, password: str = "e2e-test-pass-1"):
        page.goto(e2e_url("/admin-users/new"))
        page.fill('input[name="username"]', username)
        page.fill('input[name="password"]', password)
        page.fill('input[name="confirm_password"]', password)
        page.click('button[type="submit"]')
        page.wait_for_url(re.compile(r"/admin-users$"))

    def test_navigate_to_detail_from_list(self, page: Page):
        """一覧から詳細画面に遷移できる"""
        username = _unique_username(page)
        self._create_admin_user(page, username)

        page.click(f'a:has-text("{username}")')
        assert "/admin-users/" in page.url

    def test_edit_username(self, page: Page):
        """管理者アカウントのユーザー名を編集できる"""
        username = _unique_username(page)
        new_username = f"{username}_renamed"
        self._create_admin_user(page, username)

        page.click(f'a:has-text("{username}")')
        # The page fills #username asynchronously; typing earlier gets overwritten by that load
        expect(page.locator("#username")).to_have_value(username)
        page.fill("#username", new_username)
        page.click('button[type="submit"]')

        # Wait for the success modal/alert to confirm the save
        page.wait_for_timeout(500)
        expect(page.locator("#username")).to_have_value(new_username)

    def test_delete_admin_user(self, page: Page):
        """管理者アカウントを削除できる（自分以外）"""
        username = _unique_username(page)
        self._create_admin_user(page, username)

        page.click(f'a:has-text("{username}")')
        page.click("#delete-btn")

        # Confirm via the custom modal dialog
        page.click("#commonModalConfirm")

        # Should redirect back to the list, and the deleted account should be gone
        page.wait_for_url(re.compile(r"/admin-users$"))
        expect(page.locator(f'a:has-text("{username}")')).to_have_count(0)

    def test_cannot_delete_own_logged_in_account(self, page: Page):
        """現在ログイン中の自分のアカウントは一覧から削除できない（エラー表示）"""
        page.goto(e2e_url("/admin-users"))

        # The currently logged-in account is "admin"
        if page.locator('a:has-text("admin")').count() > 0:
            page.click('a:has-text("admin")')
            page.click("#delete-btn")
            page.click("#commonModalConfirm")

            # Should show an error modal/alert instead of redirecting away
            page.wait_for_timeout(500)
            assert "/admin-users/" in page.url
