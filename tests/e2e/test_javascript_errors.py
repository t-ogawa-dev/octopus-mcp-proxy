"""
JavaScript Error Detection Tests
Tests to catch JavaScript errors and console errors in the application
"""

import pytest
from playwright.sync_api import ConsoleMessage, Page


class TestJavaScriptErrors:
    """JavaScriptエラーを検知するテスト"""

    @pytest.fixture(autouse=True)
    def setup_error_tracking(self, page: Page):
        """各テストの前にエラー追跡をセットアップ"""
        self.js_errors = []
        self.console_errors = []
        self.network_errors = []

        # JavaScriptエラーをキャッチ
        def handle_page_error(error):
            self.js_errors.append(str(error))

        # コンソールエラーをキャッチ
        def handle_console(msg: ConsoleMessage):
            if msg.type == "error" or msg.type == "warning" and "SyntaxError" in msg.text:
                self.console_errors.append(msg.text)

        # ネットワークエラーをキャッチ (500エラーなど)
        def handle_response(response):
            if response.status >= 500:
                self.network_errors.append({"url": response.url, "status": response.status})
            # JSONを期待するAPIがHTMLを返した場合を検知
            elif response.url.startswith(page.url.split("/")[0] + "//") and "/api/" in response.url:
                content_type = response.headers.get("content-type", "")
                if "text/html" in content_type and response.status != 404:
                    # 404の場合は修正済みなのでスキップ
                    self.network_errors.append(
                        {"url": response.url, "status": response.status, "issue": "HTML returned for API endpoint"}
                    )

        page.on("pageerror", handle_page_error)
        page.on("console", handle_console)
        page.on("response", handle_response)

        yield

        # テスト後にエラーがあればアサーション失敗
        all_errors = {
            "js_errors": self.js_errors,
            "console_errors": self.console_errors,
            "network_errors": self.network_errors,
        }

        # エラーがあれば詳細を出力
        if any(all_errors.values()):
            error_report = []
            if self.js_errors:
                error_report.append(f"JavaScript Errors: {self.js_errors}")
            if self.console_errors:
                error_report.append(f"Console Errors: {self.console_errors}")
            if self.network_errors:
                error_report.append(f"Network Errors: {self.network_errors}")

            # アサーションでレポート出力
            # Note: このフィクスチャはエラーを収集するだけ、
            # 各テストで assert_no_errors() を呼び出す

    def assert_no_errors(self):
        """エラーがないことを確認"""
        errors = []
        if self.js_errors:
            errors.append(f"JavaScript Errors: {self.js_errors}")
        if self.console_errors:
            errors.append(f"Console Errors: {self.console_errors}")
        if self.network_errors:
            errors.append(f"Network Errors: {self.network_errors}")

        assert not errors, "\n".join(errors)

    def test_dashboard_no_js_errors(self, authenticated_page, page: Page):
        """ダッシュボードページでJSエラーがないことを確認"""
        page.goto("/dashboard")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1000)  # 非同期処理を待つ

        self.assert_no_errors()

    def test_mcp_services_list_no_js_errors(self, authenticated_page, page: Page):
        """MCPサービス一覧ページでJSエラーがないことを確認"""
        page.goto("/mcp-services")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1000)

        self.assert_no_errors()

    def test_accounts_list_no_js_errors(self, authenticated_page, page: Page):
        """アカウント一覧ページでJSエラーがないことを確認"""
        page.goto("/accounts")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1000)

        self.assert_no_errors()

    def test_variables_list_no_js_errors(self, authenticated_page, page: Page):
        """変数一覧ページでJSエラーがないことを確認"""
        page.goto("/variables")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1000)

        self.assert_no_errors()

    def test_connection_logs_no_js_errors(self, authenticated_page, page: Page):
        """接続ログページでJSエラーがないことを確認"""
        page.goto("/connection-logs")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1000)

        self.assert_no_errors()

    def test_templates_list_no_js_errors(self, authenticated_page, page: Page):
        """テンプレート一覧ページでJSエラーがないことを確認"""
        page.goto("/mcp-templates")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1000)

        self.assert_no_errors()

    def test_admin_settings_no_js_errors(self, authenticated_page, page: Page):
        """管理者設定ページでJSエラーがないことを確認"""
        page.goto("/connection-logs/settings")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1000)

        self.assert_no_errors()


class TestAPIResponseFormat:
    """APIレスポンス形式のテスト - HTMLではなくJSONが返されることを確認"""

    @pytest.fixture(autouse=True)
    def setup_api_tracking(self, page: Page):
        """APIレスポンスを追跡"""
        self.api_responses = []

        def handle_response(response):
            if "/api/" in response.url:
                content_type = response.headers.get("content-type", "")
                self.api_responses.append(
                    {
                        "url": response.url,
                        "status": response.status,
                        "content_type": content_type,
                        "is_json": "application/json" in content_type,
                    }
                )

        page.on("response", handle_response)
        yield

    def assert_all_api_responses_are_json(self):
        """全てのAPIレスポンスがJSON形式であることを確認"""
        non_json_responses = [
            r
            for r in self.api_responses
            if not r["is_json"] and r["status"] != 204  # 204 No Contentはボディなし
        ]

        assert not non_json_responses, f"Non-JSON API responses found: {non_json_responses}"

    def test_dashboard_api_responses(self, authenticated_page, page: Page):
        """ダッシュボードのAPIコールがJSONを返すことを確認"""
        page.goto("/dashboard")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1000)

        self.assert_all_api_responses_are_json()

    def test_mcp_services_api_responses(self, authenticated_page, page: Page):
        """MCPサービスページのAPIコールがJSONを返すことを確認"""
        page.goto("/mcp-services")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1000)

        self.assert_all_api_responses_are_json()

    def test_accounts_api_responses(self, authenticated_page, page: Page):
        """アカウントページのAPIコールがJSONを返すことを確認"""
        page.goto("/accounts")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1000)

        self.assert_all_api_responses_are_json()
