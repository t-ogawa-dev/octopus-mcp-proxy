"""
Migration consistency test: an empty database upgraded to head must contain every
table and column the models define.

Always runs against a temporary SQLite file. To also check PostgreSQL (production),
point MIGRATION_TEST_DATABASE_URL at an empty, disposable database:

    docker run -d --rm --name mig -e POSTGRES_PASSWORD=pw -p 127.0.0.1:55432:5432 postgres:16-alpine
    MIGRATION_TEST_DATABASE_URL=postgresql://postgres:pw@127.0.0.1:55432/postgres \
        pytest tests/integration/test_migrations.py -q
"""

import os

import pytest
import sqlalchemy as sa
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext

POSTGRES_URL = os.getenv("MIGRATION_TEST_DATABASE_URL")


def _flatten(diffs):
    for diff in diffs:
        # Column-level modifications are reported as nested lists
        yield from (diff if isinstance(diff, list) else [diff])


def _missing_after_upgrade(database_url):
    from flask_migrate import upgrade

    from app import create_app
    from app.config.config import Config, _database_url
    from app.models.models import db

    class MigrationConfig(Config):
        SQLALCHEMY_DATABASE_URI = _database_url(database_url)

    app = create_app(MigrationConfig)
    with app.app_context():
        with db.engine.begin() as conn:
            assert not sa.inspect(conn).get_table_names(), "the migration test database must be empty"

        upgrade(directory="db/migrations")

        with db.engine.connect() as conn:
            diffs = compare_metadata(MigrationContext.configure(conn), db.metadata)
        db.engine.dispose()

    return [d for d in _flatten(diffs) if d[0] in ("add_table", "add_column")]


def test_sqlite_upgrade_head_creates_every_model_table_and_column(tmp_path):
    assert _missing_after_upgrade(f"sqlite:///{tmp_path / 'migrations.db'}") == []


@pytest.mark.skipif(not POSTGRES_URL, reason="MIGRATION_TEST_DATABASE_URL is not set")
def test_postgres_upgrade_head_creates_every_model_table_and_column():
    assert _missing_after_upgrade(POSTGRES_URL) == []
