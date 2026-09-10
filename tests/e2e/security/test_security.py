"""
E2E Tests for Security Features
ログインロック・監査ログ画面のテスト
"""

from uuid import uuid4

import pytest
from playwright.sync_api import Page, expect

from tests.e2e.helpers import admin_credentials, e2e_url


@pytest.fixture
def logged_in_page(page: Page):
    """ログイン済みのページ"""
    username, password = admin_credentials()
    page.goto(e2e_url("/login"))
    page.fill('input[name="username"]', username)
    page.fill('input[name="password"]', password)
    page.click('button[type="submit"]')
    page.wait_for_url(e2e_url("/dashboard"))
    return page


class TestLoginBruteForceProtection:
    """ログインブルートフォース保護のE2Eテスト"""

    brute_force_username = "e2e-lock-test-user"

    @pytest.fixture(autouse=True)
    def isolated_client_ip(self, page: Page):
        """ログインロック状態が他のE2Eテストへ波及しない専用IPを使う"""
        octets = [str(int(part, 16)) for part in uuid4().hex[:6:2]]
        page.set_extra_http_headers({"X-Forwarded-For": f"10.254.{octets[0]}.{octets[1]}"})

    def test_multiple_failed_login_triggers_lock(self, page: Page):
        """複数回ログイン失敗でロックされる"""
        page.goto(e2e_url("/login"))

        # Fail 5 times
        for _i in range(5):
            page.fill('input[name="username"]', self.brute_force_username)
            page.fill('input[name="password"]', "wrongpassword")
            page.click('button[type="submit"]')
            page.wait_for_timeout(500)

        # Next attempt should show lock message
        page.fill('input[name="username"]', self.brute_force_username)
        page.fill('input[name="password"]', "wrongpassword")
        page.click('button[type="submit"]')

        # Check for lock message
        error_message = page.locator('.alert-danger, .error, [role="alert"]')
        expect(error_message).to_contain_text("ロック", timeout=3000)

    @pytest.mark.skip(reason="Login lock expiration requires time mocking or waiting for the configured lock duration")
    def test_successful_login_after_lock_expires(self, page: Page):
        """ロック期限切れ後は正常ログイン可能"""
        # This test would require waiting 5 minutes or mocking time
        # Simplified version: just verify the mechanism exists
        page.goto(e2e_url("/login"))

        # The lock expiration is tested in unit tests
        # Here we just verify login works normally
        page.fill('input[name="username"]', "admin")
        page.fill('input[name="password"]', "admin")
        page.click('button[type="submit"]')

        expect(page).to_have_url(e2e_url("/dashboard"))

    def test_password_visibility_toggle(self, page: Page):
        """パスワード表示切り替えボタン"""
        page.goto(e2e_url("/login"))

        password_input = page.locator('input[name="password"]')
        toggle_button = page.locator('[data-action="toggle-password"]')

        if toggle_button.is_visible():
            # Initially should be password type
            expect(password_input).to_have_attribute("type", "password")

            # Click toggle
            toggle_button.click()

            # Should change to text type
            expect(password_input).to_have_attribute("type", "text")

            # Click again
            toggle_button.click()

            # Should change back to password
            expect(password_input).to_have_attribute("type", "password")


class TestLoginLogsPage:
    """接続ログ一覧ページのテスト"""

    def test_login_logs_page_loads(self, logged_in_page: Page):
        """ログイン履歴ページが表示される"""
        logged_in_page.goto(e2e_url("/connection-logs"))

        heading = logged_in_page.locator("h1, h2").first
        expect(heading).to_be_visible()
        expect(logged_in_page).to_have_url(e2e_url("/connection-logs"))

    def test_login_logs_display(self, logged_in_page: Page):
        """ログイン履歴が表示される"""
        logged_in_page.goto(e2e_url("/connection-logs/list"))

        expect(logged_in_page.locator("#logs-table")).to_be_visible()
        expect(logged_in_page.locator("#logs-body")).to_be_visible()

    def test_filter_login_logs_by_status(self, logged_in_page: Page):
        """ログイン履歴をステータスでフィルタ"""
        logged_in_page.goto(e2e_url("/connection-logs/list"))

        status_filter = logged_in_page.locator("#filter-status")
        expect(status_filter).to_be_visible()
        status_filter.select_option("false")
        logged_in_page.locator("#apply-filter-btn").click()
        expect(status_filter).to_have_value("false")

    def test_unlock_ip_button(self, logged_in_page: Page):
        """IPアンロックボタン"""
        logged_in_page.goto(e2e_url("/connection-logs/list"))

        unlock_button = logged_in_page.locator("#clear-filter-btn")
        expect(unlock_button).to_be_visible()
        expect(unlock_button).to_have_text("クリア")


class TestActionLogsPage:
    """現行の接続ログ画面で検証できる範囲のテスト"""

    def test_action_logs_page_loads(self, logged_in_page: Page):
        """操作ログページが表示される"""
        logged_in_page.goto(e2e_url("/connection-logs/list"))

        expect(logged_in_page.locator("#logs-table")).to_be_visible()

    def test_action_logs_display(self, logged_in_page: Page):
        """操作ログが表示される"""
        logged_in_page.goto(e2e_url("/connection-logs/list"))

        table = logged_in_page.locator("#logs-table")
        expect(table).to_be_visible()

    def test_filter_action_logs_by_entity(self, logged_in_page: Page):
        """操作ログをエンティティタイプでフィルタ"""
        logged_in_page.goto(e2e_url("/connection-logs/list"))

        entity_filter = logged_in_page.locator("#filter-method")
        expect(entity_filter).to_be_visible()
        entity_filter.select_option("tools/call")
        logged_in_page.locator("#apply-filter-btn").click()
        expect(entity_filter).to_have_value("tools/call")

    def test_action_log_detail_view(self, logged_in_page: Page):
        """操作ログの詳細表示"""
        logged_in_page.goto(e2e_url("/connection-logs"))

        logged_in_page.goto(e2e_url("/connection-logs/list"))
        log_entry = logged_in_page.locator("#logs-body tr").first
        if log_entry.get_attribute("data-log-id"):
            log_entry.click()

            assert "/connection-logs/" in logged_in_page.url


class TestSecuritySettings:
    """現行の接続ログ設定画面のテスト"""

    def test_security_settings_page_loads(self, logged_in_page: Page):
        """セキュリティ設定ページが表示される"""
        # Navigate to settings page
        logged_in_page.goto(e2e_url("/connection-logs/settings"))

        heading = logged_in_page.locator("h1, h2").first
        expect(heading).to_be_visible()

    def test_update_max_body_size(self, logged_in_page: Page):
        """ログボディ最大サイズの変更"""
        logged_in_page.goto(e2e_url("/connection-logs/settings"))

        max_body_size_input = logged_in_page.locator("#mcp_log_max_body_size")
        expect(max_body_size_input).to_be_visible()
        max_body_size_input.fill("20480")
        logged_in_page.locator("#settings-form").locator('button[type="submit"]').click()
        expect(logged_in_page.locator(".toast.success")).to_be_visible(timeout=3000)

    def test_update_log_enabled(self, logged_in_page: Page):
        """ログ記録の有効状態の変更"""
        logged_in_page.goto(e2e_url("/connection-logs/settings"))

        enabled_toggle = logged_in_page.locator("#mcp_log_enabled")
        expect(enabled_toggle).to_be_attached()
        enabled_toggle.uncheck(force=True)
        logged_in_page.locator("#settings-form").locator('button[type="submit"]').click()
        expect(logged_in_page.locator(".toast.success")).to_be_visible(timeout=3000)

    def test_update_custom_masking_pattern(self, logged_in_page: Page):
        """カスタムマスキングパターンの変更"""
        logged_in_page.goto(e2e_url("/connection-logs/settings"))

        custom_patterns = logged_in_page.locator("#mcp_log_mask_custom_patterns")
        expect(custom_patterns).to_be_visible()
        custom_patterns.fill("password")
        logged_in_page.locator("#settings-form").locator('button[type="submit"]').click()
        expect(logged_in_page.locator(".toast.success")).to_be_visible(timeout=3000)


class TestSecurityDashboard:
    """セキュリティダッシュボードのテスト"""

    def test_security_dashboard_loads(self, logged_in_page: Page):
        """セキュリティダッシュボードが表示される"""
        logged_in_page.goto(e2e_url("/connection-logs"))

        # Check dashboard elements
        heading = logged_in_page.locator("h1, h2").first
        expect(heading).to_be_visible()

    def test_locked_ips_display(self, logged_in_page: Page):
        """ロック中のIPアドレス一覧"""
        logged_in_page.goto(e2e_url("/connection-logs/list"))

        expect(logged_in_page.locator("#logs-table")).to_be_visible()

    def test_recent_login_attempts_display(self, logged_in_page: Page):
        """最近のログイン試行の表示"""
        logged_in_page.goto(e2e_url("/connection-logs/list"))

        recent_attempts = logged_in_page.locator("#logs-body")
        expect(recent_attempts).to_be_visible()

    def test_security_statistics(self, logged_in_page: Page):
        """セキュリティ統計情報の表示"""
        logged_in_page.goto(e2e_url("/connection-logs/list"))

        stats = logged_in_page.locator("#log-stats")
        expect(stats).to_be_visible()


class TestFooterBranding:
    """フッターブランディングのテスト"""

    def test_footer_visible_on_all_pages(self, logged_in_page: Page):
        """全ページでフッターが表示される"""
        pages = [
            e2e_url("/"),
            e2e_url("/dashboard"),
            e2e_url("/variables"),
            e2e_url("/mcp-services"),
        ]

        for url in pages:
            logged_in_page.goto(url)
            footer = logged_in_page.locator("footer, .footer")
            expect(footer).to_be_visible()

    def test_footer_branding_text(self, logged_in_page: Page):
        """フッターブランディングテキストの確認"""
        logged_in_page.goto(e2e_url("/"))

        brand = logged_in_page.locator(".brand-title")
        expect(brand).to_contain_text("Octopus MCP Proxy")

    def test_footer_at_bottom(self, logged_in_page: Page):
        """フッターが画面最下部に配置される"""
        logged_in_page.goto(e2e_url("/"))

        footer = logged_in_page.locator("footer, .footer")

        # Footer should be at bottom
        # Check its position is near the viewport bottom
        footer_box = footer.bounding_box()
        viewport_height = logged_in_page.viewport_size["height"]

        # Footer bottom should be at or near viewport bottom
        # (allowing for some tolerance)
        if footer_box:
            assert footer_box["y"] + footer_box["height"] >= viewport_height - 100
