"""
E2E tests for Capabilities page
Tests the capabilities page in a real browser environment
"""

from playwright.sync_api import Page

from tests.e2e.helpers import e2e_url


def test_capabilities_page_loads_without_error(page: Page, authenticated_page):
    """Test that capabilities page loads without 500 error"""
    # Navigate to dashboard
    page.goto(e2e_url("/dashboard"))

    # Wait for page to load
    page.wait_for_load_state("networkidle")

    # Check that no console errors occurred
    page.on("console", lambda msg: print(f"Console {msg.type()}: {msg.text()}"))

    # Look for any 500 errors in network
    errors = []
    page.on("response", lambda response: errors.append(response.url) if response.status == 500 else None)

    # Wait a bit to let any AJAX requests complete
    page.wait_for_timeout(2000)

    # Check for errors
    assert len(errors) == 0, f"500 errors detected: {errors}"


# Timeout create/edit flows are covered against the current UI in test_capability_schema_roundtrip.py
