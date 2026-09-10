"""
E2E tests for Capabilities page
Tests the capabilities page in a real browser environment
"""

import json

import pytest
from playwright.sync_api import Page, expect

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


def test_create_capability_with_timeout_e2e(page: Page, authenticated_page, create_test_service):
    """Test creating a capability with timeout setting via UI"""
    service_id = create_test_service

    # Navigate to capabilities page for service
    page.goto(e2e_url(f"/services/{service_id}"))
    page.wait_for_load_state("networkidle")

    # Click "Add Capability" button
    page.click("button:has-text('Add Capability')")

    # Fill in capability form
    page.fill("input[name='name']", "e2e_test_capability")
    page.select_option("select[name='capability_type']", "tool")
    page.fill("input[name='url']", "https://api.example.com/test")
    page.fill("textarea[name='description']", "E2E test capability")
    page.fill("input[name='timeout_seconds']", "120")

    # Submit form
    page.click("button:has-text('Create')")

    # Wait for success message or redirect
    page.wait_for_timeout(1000)

    # Verify capability was created
    # Check if it appears in the list
    expect(page.locator("text=e2e_test_capability")).to_be_visible()
    expect(page.locator("text=120s")).to_be_visible()


def test_view_capability_details_with_timeout(page: Page, authenticated_page, create_test_capability):
    """Test viewing capability details shows timeout setting"""
    service_id, capability_id = create_test_capability

    # Navigate to service page
    page.goto(e2e_url(f"/services/{service_id}"))
    page.wait_for_load_state("networkidle")

    # Click on capability to view details
    page.click(f"tr[data-capability-id='{capability_id}']")

    # Verify timeout is displayed
    expect(page.locator("text=Timeout:")).to_be_visible()
    expect(page.locator("text=90 seconds")).to_be_visible()


def test_edit_capability_timeout_e2e(page: Page, authenticated_page, create_test_capability):
    """Test editing capability timeout via UI"""
    service_id, capability_id = create_test_capability

    # Navigate to service page
    page.goto(e2e_url(f"/services/{service_id}"))
    page.wait_for_load_state("networkidle")

    # Click edit button for capability
    page.click(f"tr[data-capability-id='{capability_id}'] button:has-text('Edit')")

    # Change timeout value
    page.fill("input[name='timeout_seconds']", "150")

    # Save changes
    page.click("button:has-text('Save')")

    # Wait for update
    page.wait_for_timeout(1000)

    # Verify change was saved
    page.reload()
    page.wait_for_load_state("networkidle")

    expect(page.locator("text=150s")).to_be_visible()


@pytest.fixture
def create_test_service(authenticated_page):
    """Create a test service for E2E tests"""
    from app.models.models import McpService, Service, db

    mcp_service = McpService(name="E2E Test Service", identifier="e2e-test", routing_type="subdomain")
    db.session.add(mcp_service)
    db.session.flush()

    service = Service(
        mcp_service_id=mcp_service.id, name="E2E Test App", service_type="api", mcp_url="https://api.example.com"
    )
    db.session.add(service)
    db.session.commit()

    yield service.id

    # Cleanup
    db.session.delete(service)
    db.session.delete(mcp_service)
    db.session.commit()


@pytest.fixture
def create_test_capability(authenticated_page, create_test_service):
    """Create a test capability for E2E tests"""
    from app.models.models import Capability, db

    service_id = create_test_service

    capability = Capability(
        app_id=service_id,
        name="e2e_fixture_capability",
        capability_type="tool",
        url="https://api.example.com/fixture",
        description="E2E fixture capability",
        timeout_seconds=90,
        headers=json.dumps({}),
        body_params=json.dumps({}),
    )
    db.session.add(capability)
    db.session.commit()

    yield service_id, capability.id

    # Cleanup
    db.session.delete(capability)
    db.session.commit()
