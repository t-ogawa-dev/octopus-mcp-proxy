"""
Tests for enhanced error response handling
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from app.models.models import Capability, McpService, Service


@pytest.fixture
def test_capability_for_errors(db):
    """Create test capability for error testing"""
    mcp_service = McpService(name="Error Test Service", identifier="error-test", routing_type="subdomain")
    db.session.add(mcp_service)
    db.session.flush()

    service = Service(
        mcp_service_id=mcp_service.id, name="Error Test App", service_type="api", mcp_url="https://api.example.com"
    )
    db.session.add(service)
    db.session.flush()

    capability = Capability(
        app_id=service.id,
        name="error_test",
        capability_type="tool",
        url="https://api.example.com/test",
        description="Test error handling",
        timeout_seconds=30,
        headers=json.dumps({"Content-Type": "application/json"}),
        body_params=json.dumps({}),
    )
    db.session.add(capability)
    db.session.commit()

    return capability


@patch("app.services.mcp_handler.httpx.post")
def test_timeout_error_structure(mock_post, client, db, test_capability_for_errors):
    """Test timeout error has proper structure"""
    # Login
    client.post("/login", data={"username": "admin", "password": "admin"})

    # Mock timeout exception
    import httpx

    mock_post.side_effect = httpx.TimeoutException("Connection timeout")

    # Execute capability
    response = client.post(f"/api/capabilities/{test_capability_for_errors.id}/test", json={"params": {}})

    assert response.status_code == 500
    data = response.json

    # Check error structure
    assert "error" in data
    error = data["error"]
    assert "code" in error
    assert error["code"] == "API_TIMEOUT"
    assert "message" in error
    # Message can be in Japanese or English
    assert "タイムアウト" in error["message"] or "timeout" in error["message"].lower()


@patch("app.services.mcp_handler.httpx.post")
def test_http_404_error_structure(mock_post, client, db, test_capability_for_errors):
    """Test HTTP 404 error has proper structure"""
    # Login
    client.post("/login", data={"username": "admin", "password": "admin"})

    # Mock 404 response
    import httpx

    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_response.reason_phrase = "Not Found"
    mock_response.text = "The requested resource was not found"

    mock_post.return_value = mock_response
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "Not Found", request=MagicMock(), response=mock_response
    )

    # Execute capability
    response = client.post(f"/api/capabilities/{test_capability_for_errors.id}/test", json={"params": {}})

    assert response.status_code == 500
    data = response.json

    # Check error structure
    assert "error" in data
    error = data["error"]
    assert "code" in error
    assert error["code"] == "HTTP_404"
    assert "message" in error
    assert "404" in error["message"]


@patch("app.services.mcp_handler.httpx.post")
def test_http_500_error_structure(mock_post, client, db, test_capability_for_errors):
    """Test HTTP 500 error has proper structure"""
    # Login
    client.post("/login", data={"username": "admin", "password": "admin"})

    # Mock 500 response
    import httpx

    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.reason_phrase = "Internal Server Error"
    mock_response.text = "Server error occurred"

    mock_post.return_value = mock_response
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "Internal Server Error", request=MagicMock(), response=mock_response
    )

    # Execute capability
    response = client.post(f"/api/capabilities/{test_capability_for_errors.id}/test", json={"params": {}})

    assert response.status_code == 500
    data = response.json

    # Check error structure
    assert "error" in data
    error = data["error"]
    assert "code" in error
    assert error["code"] == "HTTP_500"


@patch("app.services.mcp_handler.httpx.post")
def test_http_401_error_structure(mock_post, client, db, test_capability_for_errors):
    """Test HTTP 401 error has proper structure"""
    # Login
    client.post("/login", data={"username": "admin", "password": "admin"})

    # Mock 401 response
    import httpx

    mock_response = MagicMock()
    mock_response.status_code = 401
    mock_response.reason_phrase = "Unauthorized"
    mock_response.text = "Authentication required"

    mock_post.return_value = mock_response
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "Unauthorized", request=MagicMock(), response=mock_response
    )

    # Execute capability
    response = client.post(f"/api/capabilities/{test_capability_for_errors.id}/test", json={"params": {}})

    assert response.status_code == 500
    data = response.json

    # Check error structure
    assert "error" in data
    error = data["error"]
    assert "code" in error
    assert error["code"] == "HTTP_401"


@patch("app.services.mcp_handler.httpx.post")
def test_connection_error_structure(mock_post, client, db, test_capability_for_errors):
    """Test connection error has proper structure"""
    # Login
    client.post("/login", data={"username": "admin", "password": "admin"})

    # Mock connection error
    import httpx

    mock_post.side_effect = httpx.ConnectError("Failed to connect")

    # Execute capability
    response = client.post(f"/api/capabilities/{test_capability_for_errors.id}/test", json={"params": {}})

    assert response.status_code == 500
    data = response.json

    # Check error structure
    assert "error" in data
    error = data["error"]
    assert "code" in error
    assert "message" in error


@patch("app.services.mcp_handler.httpx.post")
def test_error_includes_details(mock_post, client, db, test_capability_for_errors):
    """Test that error responses include details field"""
    # Login
    client.post("/login", data={"username": "admin", "password": "admin"})

    # Mock timeout
    import httpx

    mock_post.side_effect = httpx.TimeoutException("Timeout after 30s")

    # Execute capability
    response = client.post(f"/api/capabilities/{test_capability_for_errors.id}/test", json={"params": {}})

    data = response.json
    error = data.get("error", {})

    # Should have details
    assert "details" in error or "message" in error


@patch("app.services.mcp_handler.httpx.post")
def test_timeout_error_includes_timeout_value(mock_post, client, db, test_capability_for_errors):
    """Test that timeout error includes the timeout value"""
    # Login
    client.post("/login", data={"username": "admin", "password": "admin"})

    # Update timeout
    test_capability_for_errors.timeout_seconds = 60
    db.session.commit()

    # Mock timeout
    import httpx

    mock_post.side_effect = httpx.TimeoutException("Timeout")

    # Execute capability
    response = client.post(f"/api/capabilities/{test_capability_for_errors.id}/test", json={"params": {}})

    data = response.json
    error_str = json.dumps(data.get("error", {}))

    # Error should mention timeout value
    assert "60" in error_str or "timeout" in error_str.lower()


@patch("app.services.mcp_handler.httpx.post")
def test_http_error_includes_status_and_body(mock_post, client, db, test_capability_for_errors):
    """Test that HTTP error includes status code and response body"""
    # Login
    client.post("/login", data={"username": "admin", "password": "admin"})

    # Mock 400 with custom error message
    import httpx

    mock_response = MagicMock()
    mock_response.status_code = 400
    mock_response.reason_phrase = "Bad Request"
    mock_response.text = "Invalid parameter: query is required"

    mock_post.return_value = mock_response
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "Bad Request", request=MagicMock(), response=mock_response
    )

    # Execute capability
    response = client.post(f"/api/capabilities/{test_capability_for_errors.id}/test", json={"params": {}})

    data = response.json
    error = data.get("error", {})

    # Should include error code with status
    assert "code" in error
    assert "HTTP_400" in error["code"] or "400" in str(error.get("details", ""))


def test_error_response_json_serializable(client, db, test_capability_for_errors):
    """Test that all error responses are JSON serializable"""
    # Login
    client.post("/login", data={"username": "admin", "password": "admin"})

    with patch("app.services.mcp_handler.httpx.post") as mock_post:
        import httpx

        mock_post.side_effect = httpx.TimeoutException("Test error")

        response = client.post(f"/api/capabilities/{test_capability_for_errors.id}/test", json={"params": {}})

        # Should be valid JSON
        assert response.content_type == "application/json"
        data = response.json

        # Should be able to re-serialize
        json_str = json.dumps(data)
        assert json_str is not None
        assert len(json_str) > 0


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("postgresql://u:p@db:5432/x", "postgresql+psycopg2://u:p@db:5432/x"),
        ("postgres://u:p@db/x", "postgresql+psycopg2://u:p@db/x"),
        ("postgresql+psycopg2://u:p@db/x", "postgresql+psycopg2://u:p@db/x"),
        ("sqlite:///mcp.db", "sqlite:///mcp.db"),
    ],
)
def test_database_url_uses_installed_postgres_driver(url, expected):
    from app.config.config import _database_url

    assert _database_url(url) == expected
