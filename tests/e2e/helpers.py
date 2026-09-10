"""Shared configuration helpers for Playwright E2E tests."""

import os


def get_base_url():
    """Return the application URL reachable from the current test environment."""
    if os.getenv("DOCKER_ENV"):
        return "http://web:5000"
    port = os.getenv("FLASK_PORT", os.getenv("PORT", "5000"))
    return f"http://localhost:{port}"


def e2e_url(path):
    """Build an absolute URL for an application path."""
    return f"{get_base_url()}{path}"


def admin_credentials():
    """Return the administrator credentials configured for the E2E target."""
    return (
        os.getenv("ADMIN_USERNAME", "admin"),
        os.getenv("ADMIN_PASSWORD", "admin"),
    )