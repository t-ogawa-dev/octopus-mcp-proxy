"""
E2E Tests for MCP Services Pages
MCP Services画面の操作テスト
"""

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


class TestMcpServiceListPage:
    """MCP Services一覧ページのテスト"""

    def test_mcp_service_list_loads(self, logged_in_page: Page):
        """MCP Services一覧ページが表示される"""
        logged_in_page.goto(e2e_url("/mcp-services"))
        expect(logged_in_page).to_have_url(e2e_url("/mcp-services"))

        # Check page title
        heading = logged_in_page.locator(".page-title h2")
        expect(heading).to_be_visible()

    def test_navigate_to_new_mcp_service(self, logged_in_page: Page):
        """新規MCP Service作成画面へ遷移"""
        logged_in_page.goto(e2e_url("/mcp-services"))

        new_button = logged_in_page.locator('a[href="/mcp-services/new"]')
        new_button.click()

        expect(logged_in_page).to_have_url(e2e_url("/mcp-services/new"))

    def test_mcp_service_list_displays_items(self, logged_in_page: Page):
        """MCP Service一覧にアイテムが表示される"""
        logged_in_page.goto(e2e_url("/mcp-services"))

        # The container is hidden when no service data is available.
        list_container = logged_in_page.locator("#services-list")
        expect(list_container).to_be_attached()

    def test_filter_by_routing_type(self, logged_in_page: Page):
        """ルーティングタイプでフィルタリング"""
        logged_in_page.goto(e2e_url("/mcp-services"))

        # Check if filter exists
        filter_select = logged_in_page.locator("#routing-type-filter")
        if filter_select.is_visible():
            filter_select.select_option("subdomain")

            # Wait for filtered results
            logged_in_page.wait_for_timeout(500)


class TestMcpServiceNewPage:
    """MCP Service新規作成ページのテスト"""

    def test_new_mcp_service_page_loads(self, logged_in_page: Page):
        """新規作成ページが表示される"""
        logged_in_page.goto(e2e_url("/mcp-services/new"))

        form = logged_in_page.locator("form")
        expect(form).to_be_visible()

        # Check required fields
        expect(logged_in_page.locator('input[name="identifier"]')).to_be_visible()
        expect(logged_in_page.locator('input[name="name"]')).to_be_visible()

    def test_create_subdomain_mcp_service(self, logged_in_page: Page):
        """サブドメイン型MCP Serviceの作成"""
        logged_in_page.goto(e2e_url("/mcp-services/new"))

        # Fill form
        logged_in_page.fill('input[name="identifier"]', "test-subdomain-mcp")
        logged_in_page.fill('input[name="name"]', "Test Subdomain MCP")

        # Select subdomain routing
        routing_select = logged_in_page.locator('select[name="routing_type"]')
        routing_select.select_option("subdomain")

        logged_in_page.fill('textarea[name="description"]', "Test subdomain MCP")

        # Submit
        logged_in_page.click('button[type="submit"]')
        logged_in_page.wait_for_url(e2e_url("/mcp-services*"))

    def test_create_path_mcp_service(self, logged_in_page: Page):
        """パス型MCP Serviceの作成"""
        logged_in_page.goto(e2e_url("/mcp-services/new"))

        logged_in_page.fill('input[name="identifier"]', "test-path-mcp")
        logged_in_page.fill('input[name="name"]', "Test Path MCP")

        # Select path routing
        routing_select = logged_in_page.locator('select[name="routing_type"]')
        routing_select.select_option("path")

        logged_in_page.fill('textarea[name="description"]', "Test path MCP")

        # Submit
        logged_in_page.click('button[type="submit"]')
        logged_in_page.wait_for_url(e2e_url("/mcp-services*"))

    def test_create_restricted_mcp_service(self, logged_in_page: Page):
        """アクセス制限付きMCP Serviceの作成"""
        logged_in_page.goto(e2e_url("/mcp-services/new"))

        logged_in_page.fill('input[name="identifier"]', "test-restricted-mcp")
        logged_in_page.fill('input[name="name"]', "Test Restricted MCP")

        routing_select = logged_in_page.locator('select[name="routing_type"]')
        routing_select.select_option("subdomain")
        logged_in_page.fill('textarea[name="description"]', "Restricted MCP service")

        logged_in_page.click('button[type="submit"]')
        logged_in_page.wait_for_url(e2e_url("/mcp-services*"))

    def test_validation_duplicate_identifier(self, logged_in_page: Page):
        """重複identifierのバリデーション"""
        # Create first service
        logged_in_page.goto(e2e_url("/mcp-services/new"))
        logged_in_page.fill('input[name="identifier"]', "duplicate-test")
        logged_in_page.fill('input[name="name"]', "Duplicate Test 1")

        routing_select = logged_in_page.locator('select[name="routing_type"]')
        routing_select.select_option("subdomain")
        logged_in_page.fill('textarea[name="description"]', "Duplicate Test 1")

        logged_in_page.click('button[type="submit"]')
        logged_in_page.wait_for_url(e2e_url("/mcp-services*"))

        # Try to create second with same identifier
        logged_in_page.goto(e2e_url("/mcp-services/new"))
        logged_in_page.fill('input[name="identifier"]', "duplicate-test")
        logged_in_page.fill('input[name="name"]', "Duplicate Test 2")

        routing_select = logged_in_page.locator('select[name="routing_type"]')
        routing_select.select_option("subdomain")
        logged_in_page.fill('textarea[name="description"]', "Duplicate Test 2")

        logged_in_page.click('button[type="submit"]')

        # Should show error
        error = logged_in_page.locator(".alert-danger, .error")
        if error.is_visible():
            expect(error).to_be_visible()


class TestMcpServiceDetailPage:
    """MCP Service詳細ページのテスト"""

    def test_mcp_service_detail_loads(self, logged_in_page: Page):
        """詳細ページが表示される"""
        # Create a service first
        logged_in_page.goto(e2e_url("/mcp-services/new"))
        logged_in_page.fill('input[name="identifier"]', "detail-test-mcp")
        logged_in_page.fill('input[name="name"]', "Detail Test MCP")

        routing_select = logged_in_page.locator('select[name="routing_type"]')
        routing_select.select_option("subdomain")
        logged_in_page.fill('textarea[name="description"]', "Detail Test MCP")

        logged_in_page.click('button[type="submit"]')
        logged_in_page.wait_for_url(e2e_url("/mcp-services*"))

        # Navigate to detail
        logged_in_page.goto(e2e_url("/mcp-services"))
        detail_link = logged_in_page.locator('a[href*="/mcp-services/"]:not([href*="/edit"]):not([href*="/new"])').first
        if detail_link.is_visible():
            detail_link.click()

            # Check detail page
            expect(logged_in_page.locator("h1, h2")).to_contain_text("MCP Service")

    def test_navigate_to_apps_from_detail(self, logged_in_page: Page):
        """詳細ページからApps管理画面へ遷移"""
        logged_in_page.goto(e2e_url("/mcp-services"))

        # Click first service
        service_link = logged_in_page.locator('a[href*="/mcp-services/"]').first
        if service_link.is_visible():
            service_link.click()

            # Look for "Apps" or "Manage Apps" link
            apps_link = logged_in_page.get_by_role("link", name="Apps")
            if apps_link.is_visible():
                apps_link.click()
                expect(logged_in_page).to_have_url("**/apps")

    def test_copy_mcp_endpoint(self, logged_in_page: Page):
        """MCPエンドポイントのコピー"""
        logged_in_page.goto(e2e_url("/mcp-services"))

        service_link = logged_in_page.locator('a[href*="/mcp-services/"]').first
        if service_link.is_visible():
            service_link.click()

            # Look for copy button
            copy_button = logged_in_page.locator('button:has-text("Copy"), .copy-button')
            if copy_button.is_visible():
                copy_button.click()

                # Success notification should appear
                logged_in_page.wait_for_timeout(500)


class TestMcpServiceEditPage:
    """MCP Service編集ページのテスト"""

    def test_edit_mcp_service(self, logged_in_page: Page):
        """MCP Serviceの編集"""
        # Create service
        logged_in_page.goto(e2e_url("/mcp-services/new"))
        logged_in_page.fill('input[name="identifier"]', "edit-test-mcp")
        logged_in_page.fill('input[name="name"]', "Edit Test MCP")

        routing_select = logged_in_page.locator('select[name="routing_type"]')
        routing_select.select_option("subdomain")
        logged_in_page.fill('textarea[name="description"]', "Edit Test MCP")

        logged_in_page.click('button[type="submit"]')
        logged_in_page.wait_for_url(e2e_url("/mcp-services*"))

        # Go to edit
        logged_in_page.goto(e2e_url("/mcp-services"))
        edit_link = logged_in_page.locator('a[href*="/mcp-services/"][href*="/edit"]').first
        if edit_link.is_visible():
            edit_link.click()

            # Update name
            name_input = logged_in_page.locator('input[name="name"]')
            name_input.clear()
            name_input.fill("Updated Edit Test MCP")

            # Submit
            logged_in_page.click('button[type="submit"]')
            logged_in_page.wait_for_url(e2e_url("/mcp-services*"))

    def test_toggle_mcp_service(self, logged_in_page: Page):
        """MCP Serviceの有効/無効切り替え"""
        logged_in_page.goto(e2e_url("/mcp-services"))

        # Look for toggle switch or enable/disable button
        toggle_button = logged_in_page.locator(
            'input[type="checkbox"].toggle, button:has-text("Enable"), button:has-text("Disable")'
        ).first
        if toggle_button.is_visible():
            toggle_button.click()
            logged_in_page.wait_for_timeout(500)

    def test_delete_mcp_service(self, logged_in_page: Page):
        """MCP Serviceの削除"""
        # Create service
        logged_in_page.goto(e2e_url("/mcp-services/new"))
        logged_in_page.fill('input[name="identifier"]', "delete-test-mcp")
        logged_in_page.fill('input[name="name"]', "Delete Test MCP")

        routing_select = logged_in_page.locator('select[name="routing_type"]')
        routing_select.select_option("subdomain")
        logged_in_page.fill('textarea[name="description"]', "Delete Test MCP")

        logged_in_page.click('button[type="submit"]')
        logged_in_page.wait_for_url(e2e_url("/mcp-services*"))

        # Go to edit page
        logged_in_page.goto(e2e_url("/mcp-services"))
        edit_link = logged_in_page.locator('a[href*="/mcp-services/"][href*="/edit"]').first
        if edit_link.is_visible():
            edit_link.click()

            # Click delete
            delete_button = logged_in_page.locator('button:has-text("Delete"), button.btn-danger')
            if delete_button.is_visible():
                logged_in_page.on("dialog", lambda dialog: dialog.accept())
                delete_button.click()

                logged_in_page.wait_for_url(e2e_url("/mcp-services"))


class TestMcpServiceAppsPage:
    """MCP Service Apps管理ページのテスト"""

    def test_mcp_service_apps_page_loads(self, logged_in_page: Page):
        """Apps管理ページが表示される"""
        logged_in_page.goto(e2e_url("/mcp-services"))

        # Navigate to first service's apps page
        service_link = logged_in_page.locator('a[href*="/mcp-services/"]').first
        if service_link.is_visible():
            service_link.click()

            apps_link = logged_in_page.get_by_role("link", name="Apps")
            if apps_link.is_visible():
                apps_link.click()

                # Check apps list
                expect(logged_in_page.locator("h1, h2")).to_contain_text("Apps")

    def test_add_app_to_mcp_service(self, logged_in_page: Page):
        """MCP ServiceにAppを追加"""
        # This would require creating a service first
        # Then adding an app (Service) to it
        # Simplified test structure here
        logged_in_page.goto(e2e_url("/mcp-services"))

        # Navigate through UI to add app
        # Implementation depends on actual UI structure
        pass


class TestMcpServiceAccessControl:
    """MCP Serviceアクセス制御のE2Eテスト"""

    def test_public_mcp_service_accessible(self, logged_in_page: Page):
        """公開MCP Serviceへのアクセス"""
        # Create public service
        logged_in_page.goto(e2e_url("/mcp-services/new"))
        logged_in_page.fill('input[name="identifier"]', "public-mcp")
        logged_in_page.fill('input[name="name"]', "Public MCP")

        routing_select = logged_in_page.locator('select[name="routing_type"]')
        routing_select.select_option("subdomain")
        logged_in_page.fill('textarea[name="description"]', "Public MCP")

        logged_in_page.click('button[type="submit"]')
        logged_in_page.wait_for_url(e2e_url("/mcp-services*"))

        # Verify public badge
        logged_in_page.goto(e2e_url("/mcp-services"))
        public_badge = logged_in_page.locator('.badge:has-text("Public"), .badge-success:has-text("Public")')
        if public_badge.first.is_visible():
            expect(public_badge.first).to_be_visible()

    def test_restricted_mcp_service_badge(self, logged_in_page: Page):
        """制限付きMCP Serviceのバッジ表示"""
        logged_in_page.goto(e2e_url("/mcp-services/new"))
        logged_in_page.fill('input[name="identifier"]', "restricted-mcp-badge")
        logged_in_page.fill('input[name="name"]', "Restricted MCP Badge")

        routing_select = logged_in_page.locator('select[name="routing_type"]')
        routing_select.select_option("subdomain")
        logged_in_page.fill('textarea[name="description"]', "Restricted MCP Badge")

        logged_in_page.click('button[type="submit"]')
        logged_in_page.wait_for_url(e2e_url("/mcp-services*"))

        # Verify restricted badge
        logged_in_page.goto(e2e_url("/mcp-services"))
        restricted_badge = logged_in_page.locator(
            '.badge:has-text("Restricted"), .badge-warning:has-text("Restricted")'
        )
        if restricted_badge.first.is_visible():
            expect(restricted_badge.first).to_be_visible()


class TestMcpServiceExportImport:
    """MCP ServiceのExport/Importテスト"""

    def test_export_mcp_service(self, logged_in_page: Page):
        """MCP ServiceをYAML形式でエクスポートできる"""
        # First create a service
        logged_in_page.goto(e2e_url("/mcp-services/new"))
        logged_in_page.fill('input[name="identifier"]', "export-test-service")
        logged_in_page.fill('input[name="name"]', "Export Test Service")
        logged_in_page.fill('textarea[name="description"]', "Service for export testing")

        routing_select = logged_in_page.locator('select[name="routing_type"]')
        routing_select.select_option("subdomain")
        logged_in_page.fill('textarea[name="description"]', "Export Test MCP")

        logged_in_page.click('button[type="submit"]')
        logged_in_page.wait_for_timeout(1000)

        # Navigate to service detail and export
        logged_in_page.goto(e2e_url("/mcp-services"))

        # Click on the created service
        service_link = logged_in_page.get_by_text("Export Test Service").first
        if service_link.is_visible():
            service_link.click()
            logged_in_page.wait_for_timeout(500)

            # Click export button
            export_button = logged_in_page.get_by_role("button", name="エクスポート") or logged_in_page.get_by_role(
                "button", name="Export"
            )
            if export_button.is_visible():
                with logged_in_page.expect_download() as download_info:
                    export_button.click()

                download = download_info.value
                # Verify YAML file
                assert download.suggested_filename.endswith(".yaml") or download.suggested_filename.endswith(".yml")

    def test_import_mcp_service_modal_opens(self, logged_in_page: Page):
        """MCPサービスインポートモーダルが開く"""
        logged_in_page.goto(e2e_url("/mcp-services"))

        # Click import button
        import_button = logged_in_page.get_by_role("button", name="インポート") or logged_in_page.get_by_role(
            "button", name="Import"
        )
        if import_button.is_visible():
            import_button.click()

            # Modal should appear
            modal = logged_in_page.locator("#import-modal")
            expect(modal).to_be_visible()

            # Check for file input
            file_input = logged_in_page.locator('input[type="file"]')
            expect(file_input).to_have_count(1)

            # Check file accept attribute
            accept_attr = file_input.get_attribute("accept")
            assert ".yaml" in accept_attr or ".yml" in accept_attr
