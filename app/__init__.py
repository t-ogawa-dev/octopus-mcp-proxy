"""
MCP Server Application Factory
"""

import logging
import os

from flask import Flask, request
from flask_cors import CORS

# Application version
__version__ = "1.0.0"

# Import extensions
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_migrate import Migrate
from werkzeug.middleware.proxy_fix import ProxyFix

from app.config.config import Config
from app.models.models import db


def setup_logging(app):
    """Configure application logging"""
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()

    # Set log level
    numeric_level = getattr(logging, log_level, logging.INFO)

    # Configure root logger
    logging.basicConfig(
        level=numeric_level, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Set Flask app logger
    app.logger.setLevel(numeric_level)

    # Set werkzeug logger (Flask dev server)
    werkzeug_logger = logging.getLogger("werkzeug")
    werkzeug_logger.setLevel(numeric_level)

    app.logger.info(f"Logging configured with level: {log_level}")


# Built-in default and the .env.example placeholder
_KNOWN_SECRET_KEYS = frozenset({"dev-secret-key-change-in-production", "your-secret-key-change-in-production"})


def _validate_production_config(app):
    """Refuse to start in production with secrets that are publicly known."""
    if os.getenv("FLASK_ENV") != "production" or app.config.get("TESTING"):
        return
    if not app.config.get("SECRET_KEY") or app.config["SECRET_KEY"] in _KNOWN_SECRET_KEYS:
        raise RuntimeError("SECRET_KEY must be set to a random value when FLASK_ENV=production")
    if os.getenv("ADMIN_PASSWORD", "admin") in ("admin", "admin123"):
        app.logger.warning("ADMIN_PASSWORD is a default value; the initial admin account is guessable until changed")


def create_app(config_class=Config):
    """Application factory pattern"""
    app = Flask(__name__, template_folder="views/templates", static_folder="assets")

    # Load configuration
    app.config.from_object(config_class)
    _validate_production_config(app)

    # Setup logging
    setup_logging(app)

    # Store admin credentials in app config (only if not already set by config class)
    if ("ADMIN_USERNAME" not in app.config or app.config.get("TESTING")) and not app.config.get("TESTING"):
        app.config["ADMIN_USERNAME"] = os.getenv("ADMIN_USERNAME", "admin")
        app.config["ADMIN_PASSWORD"] = os.getenv("ADMIN_PASSWORD", "admin123")

    app.logger.debug(f"Admin username: {app.config['ADMIN_USERNAME']}")

    if app.config.get("TRUSTED_PROXY_COUNT"):
        n = app.config["TRUSTED_PROXY_COUNT"]
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=n, x_proto=n, x_host=n)  # type: ignore[method-assign]

    # Initialize extensions
    db.init_app(app)
    Migrate(app, db, directory="db/migrations")
    # Only the MCP endpoints are meant to be called from other origins (bearer-token auth);
    # the admin UI and REST API rely on session cookies and stay same-origin.
    CORS(app, resources={r"^/mcp$": {}, r"^/admin/mcp$": {}, r"^/[^/]+/mcp/?$": {}})

    app.logger.info("Database and extensions initialized")

    # Register blueprints
    from app.controllers.admin_controller import admin_bp
    from app.controllers.admin_mcp_controller import admin_mcp_bp
    from app.controllers.api_controller import api_bp
    from app.controllers.auth_controller import auth_bp
    from app.controllers.mcp_controller import mcp_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(api_bp, url_prefix="/api")
    app.register_blueprint(mcp_bp)
    app.register_blueprint(admin_mcp_bp)

    app.logger.info("All blueprints registered")

    # MCP endpoints accept unauthenticated traffic for public services, so they are rate limited per IP
    limiter = Limiter(get_remote_address, app=app, storage_uri=app.config["RATELIMIT_STORAGE_URI"])
    mcp_limit = limiter.limit(lambda: app.config["MCP_RATE_LIMIT"])
    mcp_limit(mcp_bp)
    mcp_limit(admin_mcp_bp)

    from app.controllers.auth_controller import reject_cross_origin_request

    @app.before_request
    def csrf_protect():
        # MCP blueprints authenticate with bearer tokens, not cookies, so CSRF does not apply
        if request.blueprint in ("auth", "admin", "api"):
            return reject_cross_origin_request()
        return None

    # Global error handlers for all routes
    from flask import jsonify
    from werkzeug.exceptions import NotFound

    @app.errorhandler(404)
    def handle_global_404(e):
        """Handle 404 errors globally - return JSON for API routes, HTML for others"""
        if request.path.startswith("/api/"):
            return jsonify({"error": "Resource not found", "path": request.path}), 404
        # For non-API routes, use default HTML error page
        return e

    @app.errorhandler(500)
    def handle_global_500(e):
        """Handle 500 errors globally - return JSON for API routes, HTML for others"""
        if request.path.startswith("/api/"):
            app.logger.error("Internal server error on %s: %s", request.path, e)
            # Exception text can contain SQL, paths or secrets, so it is only logged
            return jsonify({"error": "Internal server error"}), 500
        # For non-API routes, use default HTML error page
        return e

    @app.errorhandler(429)
    def handle_rate_limited(e):
        """Rate-limit responses are JSON so MCP clients can parse them"""
        return jsonify({"error": "Too many requests", "message": str(e.description)}), 429

    # Health check endpoint
    @app.route("/health")
    def health_check():
        """Health check endpoint for monitoring and load balancers"""
        return jsonify({"status": "healthy", "version": __version__}), 200

    return app
