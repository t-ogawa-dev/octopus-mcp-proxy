"""
Configuration settings for MCP Server
"""

import os
from datetime import timedelta


def _database_url(url: str) -> str:
    """Pin bare postgresql:// URLs to psycopg2, the driver in requirements.txt.

    SQLAlchemy 2.1 switched the default PostgreSQL driver to psycopg (v3), which is not installed.
    """
    for prefix in ("postgresql://", "postgres://"):
        if url.startswith(prefix):
            return "postgresql+psycopg2://" + url[len(prefix) :]
    return url


class Config:
    """Base configuration"""

    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
    SQLALCHEMY_DATABASE_URI = _database_url(os.getenv("DATABASE_URL", "sqlite:///mcp.db"))
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Admin authentication
    ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin")

    # Admin MCP API key (Bearer token for /admin/mcp endpoint)
    ADMIN_API_KEY = os.getenv("ACCELMCP_ADMIN_API_KEY", "")

    # Flask settings
    DEBUG = os.getenv("FLASK_DEBUG", "False").lower() == "true"
    TESTING = False

    # Streamable HTTP session store backend.
    # When set, MCP/Admin-MCP Streamable HTTP sessions are shared via Redis so the MCP
    # endpoint can be scaled across replicas/hosts. When unset, an in-process store is
    # used (fine for a single container). Example: redis://redis:6379/0
    REDIS_URL = os.getenv("REDIS_URL")

    # Largest accepted request body (bytes); larger requests get 413
    MAX_CONTENT_LENGTH = int(os.getenv("MAX_CONTENT_LENGTH", str(10 * 1024 * 1024)))

    # Number of reverse proxies in front of the app whose X-Forwarded-* headers are trusted.
    # 0 (default) ignores the headers; set to 1 behind the bundled Caddy.
    TRUSTED_PROXY_COUNT = int(os.getenv("TRUSTED_PROXY_COUNT", "0"))

    # Per-client-IP rate limit for the MCP endpoints (Flask-Limiter syntax)
    RATELIMIT_ENABLED = os.getenv("RATELIMIT_ENABLED", "true").lower() == "true"
    MCP_RATE_LIMIT = os.getenv("MCP_RATE_LIMIT", "600 per minute")
    # Shared across replicas through Redis when available
    RATELIMIT_STORAGE_URI = os.getenv("RATELIMIT_STORAGE_URI") or os.getenv("REDIS_URL") or "memory://"
    # A rate-limit storage outage must not take the MCP endpoints down
    RATELIMIT_SWALLOW_ERRORS = True
    RATELIMIT_HEADERS_ENABLED = True

    # Session settings
    PERMANENT_SESSION_LIFETIME = timedelta(hours=int(os.getenv("SESSION_LIFETIME_HOURS", "12")))
    # Defaults to Secure in production (served over HTTPS by Caddy); override with SESSION_COOKIE_SECURE
    SESSION_COOKIE_SECURE = (
        os.getenv("SESSION_COOKIE_SECURE", str(os.getenv("FLASK_ENV") == "production")).lower() == "true"
    )
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    # Allow cookies to work across localhost and lvh.me (development only)
    SESSION_COOKIE_DOMAIN = os.getenv("SESSION_COOKIE_DOMAIN", None)

    # Template Repository Configuration
    TEMPLATE_REPOSITORY_URL = os.getenv(
        "TEMPLATE_REPOSITORY_URL",
        "https://raw.githubusercontent.com/t-ogawa-dev/octopus-mcp-proxy/main/data/builtin_templates",
    )
    TEMPLATE_INDEX_FILE = os.getenv("TEMPLATE_INDEX_FILE", "index.yaml")
    TEMPLATE_VERSIONS_DIR = os.getenv("TEMPLATE_VERSIONS_DIR", "versions")


class DevelopmentConfig(Config):
    """Development configuration"""

    DEBUG = True


class ProductionConfig(Config):
    """Production configuration"""

    DEBUG = False


class TestingConfig(Config):
    """Testing configuration"""

    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    RATELIMIT_ENABLED = False


# Configuration dictionary
config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
    "default": DevelopmentConfig,
}
