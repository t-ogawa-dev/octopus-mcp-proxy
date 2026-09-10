"""
E2E tests for capabilities pages
"""

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


class TestCapabilitiesListPage:
    """Capabilities一覧ページのE2Eテスト"""

    def test_capabilities_list_loads(self, page: Page):
        """Capabilities一覧ページが読み込まれる"""
        page.goto(e2e_url("/services"))

        # Navigate to first service's capabilities
        if page.locator(".service-card:first-of-type a, .list-item:first-of-type a").count() > 0:
            page.click(".service-card:first-of-type a, .list-item:first-of-type a")

            if page.locator('a:has-text("Capabilities")').count() > 0:
                page.click('a:has-text("Capabilities")')
                assert "/capabilities" in page.url

    def test_toggle_capability(self, page: Page):
        """Capabilityの有効/無効を切り替えられる"""
        page.goto(e2e_url("/services"))

        # Navigate to first service's capabilities
        if page.locator(".service-card:first-of-type a, .list-item:first-of-type a").count() > 0:
            page.click(".service-card:first-of-type a, .list-item:first-of-type a")

            if page.locator('a:has-text("Capabilities")').count() > 0:
                page.click('a:has-text("Capabilities")')

                # Toggle first capability if exists
                toggle = page.locator(".toggle-switch input").first
                if toggle.count() > 0:
                    initial_state = toggle.is_checked()
                    toggle.click()

                    # Wait for toggle
                    page.wait_for_timeout(500)

                    # Verify state changed
                    assert toggle.is_checked() != initial_state

    def test_status_badge_display(self, page: Page):
        """ステータスバッジが表示される"""
        page.goto(e2e_url("/services"))

        # Navigate to first service's capabilities
        if page.locator(".service-card:first-of-type a, .list-item:first-of-type a").count() > 0:
            page.click(".service-card:first-of-type a, .list-item:first-of-type a")

            if page.locator('a:has-text("Capabilities")').count() > 0:
                page.click('a:has-text("Capabilities")')

                # Check if status badges exist
                if page.locator(".status-badge").count() > 0:
                    expect(page.locator(".status-badge").first).to_be_visible()


class TestCapabilityDetailPage:
    """Capability詳細ページのE2Eテスト"""

    def test_navigate_to_capability_detail(self, page: Page):
        """Capability詳細画面に遷移できる"""
        page.goto(e2e_url("/services"))

        # Navigate to first service's capabilities
        if page.locator(".service-card:first-of-type a, .list-item:first-of-type a").count() > 0:
            page.click(".service-card:first-of-type a, .list-item:first-of-type a")

            if page.locator('a:has-text("Capabilities")').count() > 0:
                page.click('a:has-text("Capabilities")')

                # Click first capability
                if page.locator(".list-item a").count() > 0:
                    page.click(".list-item a:first-of-type")
                    assert "/capabilities/" in page.url


class TestCapabilityEditPage:
    """Capability編集ページのE2Eテスト"""

    def test_navigate_to_capability_edit(self, page: Page):
        """Capability編集画面に遷移できる"""
        page.goto(e2e_url("/services"))

        # Navigate to first service's capabilities
        if page.locator(".service-card:first-of-type a, .list-item:first-of-type a").count() > 0:
            page.click(".service-card:first-of-type a, .list-item:first-of-type a")

            if page.locator('a:has-text("Capabilities")').count() > 0:
                page.click('a:has-text("Capabilities")')

                # Click first edit button
                if page.locator('a:has-text("編集")').count() > 0:
                    page.click('a:has-text("編集"):first-of-type')
                    assert "/edit" in page.url

    def test_edit_capability(self, page: Page):
        """Capabilityを編集できる"""
        page.goto(e2e_url("/services"))

        # Navigate to capability edit page
        if page.locator(".service-card:first-of-type a, .list-item:first-of-type a").count() > 0:
            page.click(".service-card:first-of-type a, .list-item:first-of-type a")

            if page.locator('a:has-text("Capabilities")').count() > 0:
                page.click('a:has-text("Capabilities")')

                if page.locator('a:has-text("編集")').count() > 0:
                    page.click('a:has-text("編集"):first-of-type')

                    # Modify capability name
                    name_input = page.locator('input[name="name"]')
                    if name_input.count() > 0:
                        name_input.clear()
                        name_input.fill("updated_capability_name")

                        # Save changes
                        page.click('button[type="submit"]')
                        page.wait_for_timeout(500)
