"""
E2E Test Configuration
"""

import pytest

from tests.e2e.helpers import admin_credentials, get_base_url


@pytest.fixture(scope="session")
def base_url():
    """Base URL for E2E tests"""
    return get_base_url()


@pytest.fixture(scope="session")
def admin_credentials_fixture():
    """Administrator credentials configured for the E2E target."""
    return admin_credentials()


@pytest.fixture
def authenticated_page(page, base_url, admin_credentials_fixture):
    """Pre-authenticated page fixture"""
    username, password = admin_credentials_fixture
    page.goto(f"{base_url}/login")
    page.wait_for_selector('input[name="username"]')
    page.fill('input[name="username"]', username)
    page.fill('input[name="password"]', password)

    # Use expect_navigation like test_login.py
    with page.expect_navigation():
        page.locator('button[type="submit"]').click()

    page.wait_for_load_state("networkidle")

    # Verify we're authenticated (not on login page anymore)
    if "/login" in page.url:
        raise Exception(f"Authentication failed - still on login page: {page.url}")

    return page
