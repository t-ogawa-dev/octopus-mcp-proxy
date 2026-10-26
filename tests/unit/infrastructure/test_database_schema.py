"""
Database Migration Status Tests
Tests to ensure database schema is up to date with models
"""

from sqlalchemy import inspect


def test_capabilities_table_has_timeout_seconds(app, db):
    """Verify timeout_seconds column exists in capabilities table"""
    with app.app_context():
        inspector = inspect(db.engine)
        columns = [col["name"] for col in inspector.get_columns("capabilities")]

        assert (
            "timeout_seconds" in columns
        ), "timeout_seconds column is missing from capabilities table. Run: flask db upgrade"


def test_capabilities_table_has_access_control(app, db):
    """Verify access_control column exists in capabilities table"""
    with app.app_context():
        inspector = inspect(db.engine)
        columns = [col["name"] for col in inspector.get_columns("capabilities")]

        assert (
            "access_control" in columns
        ), "access_control column is missing from capabilities table. Run: flask db upgrade"


def test_all_model_columns_exist_in_database(app, db):
    """Verify all model columns exist in the actual database schema"""

    with app.app_context():
        inspector = inspect(db.engine)
        errors = []

        # Check Capability model
        capability_columns = {col["name"] for col in inspector.get_columns("capabilities")}
        expected_capability_cols = {
            "id",
            "app_id",
            "name",
            "capability_type",
            "url",
            "headers",
            "body_params",
            "template_content",
            "description",
            "access_control",
            "is_enabled",
            "timeout_seconds",
            "created_at",
            "updated_at",
        }
        missing_capability = expected_capability_cols - capability_columns
        if missing_capability:
            errors.append(f"capabilities table missing: {missing_capability}")

        # Check Service (apps) model
        service_columns = {col["name"] for col in inspector.get_columns("apps")}
        expected_service_cols = {
            "id",
            "mcp_service_id",
            "name",
            "service_type",
            "mcp_url",
            "stdio_command",
            "stdio_args",
            "stdio_env",
            "description",
            "is_enabled",
            "created_at",
            "updated_at",
        }
        missing_service = expected_service_cols - service_columns
        if missing_service:
            errors.append(f"apps table missing: {missing_service}")

        assert not errors, "Database schema mismatch. Run: flask db upgrade\n" + "\n".join(errors)
