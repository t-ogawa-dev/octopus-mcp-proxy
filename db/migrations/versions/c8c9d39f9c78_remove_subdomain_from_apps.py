"""remove_subdomain_from_apps

Revision ID: c8c9d39f9c78
Revises: 8d4f3e2a1b5c
Create Date: 2025-11-25 18:10:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c8c9d39f9c78'
down_revision = '8d4f3e2a1b5c'
branch_labels = None
depends_on = None


def upgrade():
    # The unique constraint on subdomain was auto-named by the database back
    # when the table was still called "services" (e.g. "services_subdomain_key"
    # on Postgres), not literally "subdomain" -- look up the real name instead
    # of assuming it.
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    uq_name = next(
        (uq['name'] for uq in inspector.get_unique_constraints('apps')
         if uq.get('column_names') == ['subdomain']),
        None
    )
    if uq_name:
        op.drop_constraint(uq_name, 'apps', type_='unique')
    else:
        # Fall back in case it was created as a plain index rather than a
        # unique constraint.
        idx_name = next(
            (ix['name'] for ix in inspector.get_indexes('apps')
             if ix.get('column_names') == ['subdomain']),
            None
        )
        if idx_name:
            op.drop_index(idx_name, table_name='apps')

    # Remove subdomain column from apps table. Batch mode lets SQLite rebuild the
    # table, since its unnamed UNIQUE(subdomain) cannot be dropped by name above.
    with op.batch_alter_table('apps', schema=None) as batch_op:
        batch_op.drop_column('subdomain')


def downgrade():
    # Re-add subdomain column
    op.add_column('apps', sa.Column('subdomain', sa.String(50), nullable=True))
    op.create_index('subdomain', 'apps', ['subdomain'], unique=True)
