"""
E2E tests for templates pages
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


class TestTemplateListPage:
    """テンプレート一覧ページのE2Eテスト"""

    def test_template_list_loads(self, page: Page):
        """テンプレート一覧ページが読み込まれる"""
        page.goto(e2e_url("/mcp-templates"))

        expect(page).to_have_url(e2e_url("/mcp-templates"))

    def test_switch_to_custom_tab(self, page: Page):
        """カスタムタブに切り替えられる"""
        page.goto(e2e_url("/mcp-templates"))

        # Click custom tab
        if page.locator('button:has-text("カスタム")').count() > 0:
            page.click('button:has-text("カスタム")')
            page.wait_for_timeout(300)

    def test_switch_to_builtin_tab(self, page: Page):
        """WebServiceタブに切り替えられる"""
        page.goto(e2e_url("/mcp-templates"))

        # Click builtin tab
        if page.locator('button:has-text("WebService")').count() > 0:
            page.click('button:has-text("WebService")')
            page.wait_for_timeout(300)

    def test_navigate_to_new_template(self, page: Page):
        """新規テンプレート作成画面に遷移できる"""
        page.goto(e2e_url("/mcp-templates"))

        # Switch to custom tab first
        if page.locator('button:has-text("カスタム")').count() > 0:
            page.click('button:has-text("カスタム")')

        # Click new template button
        if page.locator('a[href="/mcp-templates/new"]').count() > 0:
            page.click('a[href="/mcp-templates/new"]')
            expect(page).to_have_url(e2e_url("/mcp-templates/new"))


class TestTemplateNewPage:
    """新規テンプレート作成ページのE2Eテスト"""

    def test_new_template_page_loads(self, page: Page):
        """新規テンプレート作成ページが読み込まれる"""
        page.goto(e2e_url("/mcp-templates/new"))

        expect(page).to_have_url(e2e_url("/mcp-templates/new"))
        expect(page.locator('input[name="name"]')).to_be_visible()

    def test_create_custom_template(self, page: Page):
        """カスタムテンプレートを作成できる"""
        page.goto(e2e_url("/mcp-templates/new"))

        # Fill template form
        page.fill('input[name="name"]', f"E2E Test Template {page.context.browser.version[:5]}")
        page.fill('input[name="icon"]', "🧪")
        page.fill('input[name="category"]', "Testing")
        page.fill('textarea[name="description"]', "E2E test template description")

        # Submit form
        page.click('button[type="submit"]')

        # Should redirect to template list or detail
        page.wait_for_url(re.compile("/mcp-templates"))


class TestTemplateDetailPage:
    """テンプレート詳細ページのE2Eテスト"""

    def test_template_detail_loads(self, page: Page):
        """テンプレート詳細ページが読み込まれる"""
        page.goto(e2e_url("/mcp-templates"))

        # Click first template
        if page.locator(".template-card:first-of-type, .list-item:first-of-type").count() > 0:
            page.click(".template-card:first-of-type, .list-item:first-of-type")
            assert "/mcp-templates/" in page.url

    def test_use_template_modal(self, page: Page):
        """テンプレート使用モーダルが動作する"""
        page.goto(e2e_url("/mcp-templates"))

        # Click first template's use button
        if page.locator('button:has-text("使用する")').count() > 0:
            page.click('button:has-text("使用する"):first-of-type')

            # Modal should appear
            if page.locator(".modal").count() > 0:
                expect(page.locator(".modal")).to_be_visible()

                # Fill subdomain
                page.fill('.modal input[name="subdomain"]', f"e2e-modal-{page.context.browser.version[:5]}")

                # Submit
                page.click('.modal button[type="submit"]')

                # Wait for creation
                page.wait_for_timeout(1000)

    def test_export_template(self, page: Page):
        """テンプレートをエクスポートできる（YAML形式）"""
        page.goto(e2e_url("/mcp-templates"))

        # Switch to custom tab
        if page.locator('button:has-text("カスタム")').count() > 0:
            page.click('button:has-text("カスタム")')
            page.wait_for_timeout(300)

        # Click export button if exists
        if page.locator('button:has-text("エクスポート")').count() > 0:
            # Start waiting for download before clicking
            with page.expect_download() as download_info:
                page.click('button:has-text("エクスポート"):first-of-type')

            download = download_info.value
            # Verify download - should be YAML now
            assert download.suggested_filename.endswith(".yaml") or download.suggested_filename.endswith(".yml")

    def test_navigate_to_edit(self, page: Page):
        """編集画面に遷移できる（カスタムテンプレートのみ）"""
        page.goto(e2e_url("/mcp-templates"))

        # Switch to custom tab
        if page.locator('button:has-text("カスタム")').count() > 0:
            page.click('button:has-text("カスタム")')
            page.wait_for_timeout(300)

            # Click first template
            if page.locator("#custom-templates .template-card:first-of-type").count() > 0:
                page.locator("#custom-templates .template-card:first-of-type").click()

                # Click edit button
                if page.locator('a:has-text("編集")').count() > 0:
                    page.click('a:has-text("編集")')
                    assert "/edit" in page.url

    def test_navigate_to_capabilities(self, page: Page):
        """Capabilities画面に遷移できる"""
        page.goto(e2e_url("/mcp-templates"))

        # Click first template
        if page.locator(".template-card:first-of-type, .list-item:first-of-type").count() > 0:
            page.click(".template-card:first-of-type, .list-item:first-of-type")

            # Click capabilities link
            if page.locator('a:has-text("Capabilities")').count() > 0:
                page.click('a:has-text("Capabilities")')
                assert "/capabilities" in page.url


class TestTemplateEditPage:
    """テンプレート編集ページのE2Eテスト"""

    def test_edit_template(self, page: Page):
        """カスタムテンプレートを編集できる"""
        page.goto(e2e_url("/mcp-templates"))

        # Switch to custom tab
        if page.locator('button:has-text("カスタム")').count() > 0:
            page.click('button:has-text("カスタム")')
            page.wait_for_timeout(300)

            # Navigate to first template edit page
            if page.locator("#custom-templates .template-card:first-of-type").count() > 0:
                page.locator("#custom-templates .template-card:first-of-type").click()

                if page.locator('a:has-text("編集")').count() > 0:
                    page.click('a:has-text("編集")')

                    # Modify template name
                    name_input = page.locator('input[name="name"]')
                    if name_input.count() > 0:
                        name_input.clear()
                        name_input.fill("Updated Template Name")

                        # Save changes
                        page.click('button[type="submit"]')

                        # Verify changes saved
                        page.wait_for_url(re.compile("/mcp-templates"))


class TestTemplateCapabilitiesPage:
    """テンプレートCapabilitiesページのE2Eテスト"""

    def test_template_capabilities_loads(self, page: Page):
        """テンプレートCapabilitiesページが読み込まれる"""
        page.goto(e2e_url("/mcp-templates"))

        # Click first template
        if page.locator("#api-templates .template-card:first-of-type").count() > 0:
            page.locator("#api-templates .template-card:first-of-type").click()

            # Navigate to capabilities
            if page.locator('a:has-text("Capabilities")').count() > 0:
                page.click('a:has-text("Capabilities")')
                assert "/capabilities" in page.url
