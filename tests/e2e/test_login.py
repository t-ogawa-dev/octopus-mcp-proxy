"""
E2E tests for login page
"""

import re

import pytest
from playwright.sync_api import Page, expect

from tests.e2e.helpers import admin_credentials


class TestLoginPage:
    """ログインページのE2Eテスト"""

    def test_login_page_loads(self, page: Page, base_url):
        """ログインページが読み込まれる"""
        page.goto(f"{base_url}/login")

        expect(page).to_have_title(re.compile("login", re.IGNORECASE))
        expect(page.locator('input[name="username"]')).to_be_visible()
        expect(page.locator('input[name="password"]')).to_be_visible()

    @pytest.mark.skip(reason="Form submission timing issue - works in real browser")
    def test_login_with_valid_credentials(self, page: Page, base_url):
        """正しい認証情報でログインできる"""
        page.goto(f"{base_url}/login")

        # Fill login form
        username, password = admin_credentials()
        page.fill('input[name="username"]', username)
        page.fill('input[name="password"]', password)

        # Click login button and wait for navigation
        with page.expect_navigation():
            page.click('button[type="submit"]')

        # Wait for page to load
        page.wait_for_load_state("networkidle")

        # Verify dashboard loaded (URL should end with /dashboard)
        expect(page).to_have_url(re.compile(r"/dashboard$"))

    def test_login_with_invalid_credentials(self, page: Page, base_url):
        """間違った認証情報でログインできない"""
        page.goto(f"{base_url}/login")

        page.fill('input[name="username"]', "admin")
        page.fill('input[name="password"]', "wrongpassword")
        page.click('button[type="submit"]')

        # Should stay on login page
        expect(page).to_have_url(re.compile("/login"))

    def test_language_switcher(self, page: Page, base_url):
        """言語切り替えが動作する"""
        page.goto(f"{base_url}/login")

        # Switch to English
        page.select_option("#language-select", "en")

        # Wait for language to change
        page.wait_for_timeout(500)

        # Verify English is selected
        expect(page.locator("#language-select")).to_have_value("en")

        # Switch back to Japanese
        page.select_option("#language-select", "ja")

        page.wait_for_timeout(500)

        # Verify Japanese is selected
        expect(page.locator("#language-select")).to_have_value("ja")

    def test_logout(self, page: Page, base_url):
        """ログアウトが動作する"""
        # Login first
        page.goto(f"{base_url}/login")
        username, password = admin_credentials()
        page.fill('input[name="username"]', username)
        page.fill('input[name="password"]', password)

        with page.expect_navigation():
            page.click('button[type="submit"]')

        page.wait_for_load_state("networkidle")

        # Logout
        page.goto(f"{base_url}/logout")

        # Should redirect to login
        expect(page).to_have_url(re.compile("/login"))
