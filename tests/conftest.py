"""
Pytest configuration and fixtures for testing
"""

import os

import pytest

from app import create_app
from app.config.config import Config
from app.models.models import db as _db


class TestConfig(Config):
    """Test configuration"""

    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False
    SECRET_KEY = "test-secret-key"
    ADMIN_USERNAME = "admin"
    ADMIN_PASSWORD = "admin"
    RATELIMIT_ENABLED = False


@pytest.fixture(scope="session")
def app():
    """Create application for testing"""
    os.environ["TESTING"] = "1"

    _app = create_app(TestConfig)

    with _app.app_context():
        _db.create_all()
        yield _app
        _db.drop_all()

    # Cleanup
    os.environ.pop("TESTING", None)


@pytest.fixture(scope="function")
def db(app):
    """Create database for each test"""
    with app.app_context():
        _db.create_all()
        yield _db
        _db.session.remove()
        _db.drop_all()


@pytest.fixture(scope="function")
def client(app, db):
    """Create test client"""
    return app.test_client()


@pytest.fixture(scope="function")
def runner(app):
    """Create test CLI runner"""
    return app.test_cli_runner()


@pytest.fixture(scope="function")
def auth_client(client, app):
    """Create authenticated test client"""
    with client.session_transaction() as sess:
        sess["admin_logged_in"] = True
        sess["admin_username"] = "admin"
    return client


@pytest.fixture
def sample_mcp_service(db):
    """Create sample MCP service for testing"""
    from app.models.models import McpService

    mcp_service = McpService(
        identifier="test-mcp-service", name="Test MCP Service", routing_type="subdomain", access_control="public"
    )
    db.session.add(mcp_service)
    db.session.commit()
    return mcp_service


@pytest.fixture
def sample_service(db, sample_mcp_service):
    """Create sample service (app) for testing"""
    from app.models.models import Service

    service = Service(
        mcp_service_id=sample_mcp_service.id,
        name="Test Service",
        service_type="api",
        description="Test service description",
        common_headers='{"Authorization": "Bearer token"}',
    )
    db.session.add(service)
    db.session.commit()
    return service


@pytest.fixture
def sample_capability(db, sample_service):
    """Create sample capability for testing"""
    from app.models.models import Capability

    capability = Capability(
        app_id=sample_service.id,
        name="test_capability",
        capability_type="tool",
        url="https://api.example.com/test",
        headers='{"Content-Type": "application/json"}',
        body_params='{"param1": "value1"}',
        description="Test capability",
        is_enabled=True,
    )
    db.session.add(capability)
    db.session.commit()
    return capability


@pytest.fixture
def sample_account(db):
    """Create sample connection account for testing"""
    from app.models.models import ConnectionAccount

    account = ConnectionAccount(name="Test Account", bearer_token="test_bearer_token_123", notes="Test account notes")
    db.session.add(account)
    db.session.commit()
    return account


@pytest.fixture
def sample_template(db):
    """Create sample service template for testing"""
    from app.models.models import McpServiceTemplate

    template = McpServiceTemplate(
        name="Test Template",
        template_type="custom",
        service_type="api",
        description="Test template description",
        common_headers="{}",
        icon="🧪",
        category="Testing",
    )
    db.session.add(template)
    db.session.commit()
    return template


@pytest.fixture
def sample_capability_template(db, sample_template):
    """Create sample capability template for testing"""
    from app.models.models import McpCapabilityTemplate

    cap_template = McpCapabilityTemplate(
        service_template_id=sample_template.id,
        name="test_template_capability",
        capability_type="tool",
        url="https://api.example.com/template",
        headers='{"Content-Type": "application/json"}',
        body_params='{"param": "value"}',
        description="Test capability template",
    )
    db.session.add(cap_template)
    db.session.commit()
    return cap_template
