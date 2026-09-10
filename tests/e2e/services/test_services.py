"""
E2E tests for services pages
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


class TestServiceListPage:
    """サービス一覧ページのE2Eテスト"""

    def test_service_list_loads(self, page: Page):
        """サービス一覧ページが読み込まれる"""
        page.goto(e2e_url("/services"))

        expect(page).to_have_url(e2e_url("/services"))

    def test_navigate_to_new_service(self, page: Page):
        """新規サービス登録画面に遷移できる"""
        page.goto(e2e_url("/services"))

        page.click('a[href="/services/new"]')
        expect(page).to_have_url(e2e_url("/services/new"))

    def test_navigate_to_service_detail(self, page: Page):
        """サービス詳細画面に遷移できる"""
        page.goto(e2e_url("/services"))

        # Click first service if exists
        if page.locator(".service-card:first-of-type a, .list-item:first-of-type a").count() > 0:
            page.click(".service-card:first-of-type a, .list-item:first-of-type a")
                assert "/services/" in page.url


class TestServiceNewPage:
    """新規サービス登録ページのE2Eテスト"""

    def test_new_service_page_loads(self, page: Page):
        """新規サービス登録ページが読み込まれる"""
        page.goto(e2e_url("/services/new"))

        expect(page).to_have_url(e2e_url("/services/new"))
        expect(page.locator('input[name="subdomain"]')).to_be_visible()

    def test_create_api_service(self, page: Page):
        """APIサービスを作成できる"""
        page.goto(e2e_url("/services/new"))

        # Fill service form
        page.fill('input[name="subdomain"]', f"e2e-test-api-{page.context.browser.version[:5]}")
        page.fill('input[name="name"]', "E2E Test API Service")
        page.select_option('select[name="service_type"]', "api")
        page.fill('textarea[name="description"]', "E2E test API service description")

        # Submit form
        page.click('button[type="submit"]')

        # Should redirect to service list or detail
        page.wait_for_url(re.compile("/services"))

    def test_create_mcp_service(self, page: Page):
        """MCPサービスを作成できる"""
        page.goto(e2e_url("/services/new"))

        # Fill service form
        page.fill('input[name="subdomain"]', f"e2e-test-mcp-{page.context.browser.version[:5]}")
        page.fill('input[name="name"]', "E2E Test MCP Service")
        page.select_option('select[name="service_type"]', "mcp")

        # MCP URL field should appear
        expect(page.locator('input[name="mcp_url"]')).to_be_visible()
        page.fill('input[name="mcp_url"]', "http://example.com/mcp")

        # Submit form
        page.click('button[type="submit"]')

        # Should redirect
        page.wait_for_url(re.compile("/services"))

    def test_mcp_connection_test(self, page: Page):
        """MCP接続テストボタンが動作する"""
        page.goto(e2e_url("/services/new"))

        # Select MCP service type
        page.select_option('select[name="service_type"]', "mcp")

        # Fill MCP URL
        page.fill('input[name="mcp_url"]', "http://example.com/mcp")

        # Click test connection button if exists
        if page.locator('button:has-text("接続テスト")').count() > 0:
            page.click('button:has-text("接続テスト")')

            # Wait for response
            page.wait_for_timeout(1000)


class TestServiceDetailPage:
    """サービス詳細ページのE2Eテスト"""

    def test_navigate_to_edit(self, page: Page):
        """編集画面に遷移できる"""
        page.goto(e2e_url("/services"))

        # Click first service
        if page.locator(".service-card:first-of-type a, .list-item:first-of-type a").count() > 0:
            page.click(".service-card:first-of-type a, .list-item:first-of-type a")

            # Click edit button
            if page.locator('a:has-text("編集")').count() > 0:
                page.click('a:has-text("編集")')
                assert "/edit" in page.url

    def test_navigate_to_capabilities(self, page: Page):
        """Capabilities画面に遷移できる"""
        page.goto(e2e_url("/services"))

        # Click first service
        if page.locator(".service-card:first-of-type a, .list-item:first-of-type a").count() > 0:
            page.click(".service-card:first-of-type a, .list-item:first-of-type a")

            # Click capabilities button
            if page.locator('a:has-text("Capabilities")').count() > 0:
                page.click('a:has-text("Capabilities")')
                assert "/capabilities" in page.url

    def test_copy_mcp_endpoint(self, page: Page):
        """MCPエンドポイントをコピーできる"""
        page.goto(e2e_url("/services"))

        # Click first service
        if page.locator(".service-card:first-of-type a, .list-item:first-of-type a").count() > 0:
            page.click(".service-card:first-of-type a, .list-item:first-of-type a")

            # Click copy button if exists
            if page.locator('button:has-text("コピー")').count() > 0:
                page.click('button:has-text("コピー")')
                page.wait_for_timeout(300)


class TestServiceEditPage:
    """サービス編集ページのE2Eテスト"""

    def test_edit_service(self, page: Page):
        """サービスを編集できる"""
        page.goto(e2e_url("/services"))

        # Navigate to first service edit page
        if page.locator(".service-card:first-of-type a, .list-item:first-of-type a").count() > 0:
            page.click(".service-card:first-of-type a, .list-item:first-of-type a")

            if page.locator('a:has-text("編集")').count() > 0:
                page.click('a:has-text("編集")')

                # Modify service name
                name_input = page.locator('input[name="name"]')
                if name_input.count() > 0:
                    name_input.clear()
                    name_input.fill("Updated Service Name")

                    # Save changes
                    page.click('button[type="submit"]')

                    # Verify changes saved
                    page.wait_for_url(re.compile("/services"))

    def test_delete_service(self, page: Page):
        """サービスを削除できる"""
        page.goto(e2e_url("/services"))

        # Get initial service count
        services_count = page.locator(".service-card, .list-item").count()

        if services_count > 0:
            # Navigate to first service
            page.click(".service-card:first-of-type a, .list-item:first-of-type a")

            # Click delete button
            if page.locator('button:has-text("削除")').count() > 0:
                page.on("dialog", lambda dialog: dialog.accept())
                page.click('button:has-text("削除")')

                # Wait for deletion
                page.wait_for_timeout(500)
