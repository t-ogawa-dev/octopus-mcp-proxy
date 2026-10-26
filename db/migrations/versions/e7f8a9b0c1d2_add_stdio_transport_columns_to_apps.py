"""add stdio transport columns to apps

Revision ID: e7f8a9b0c1d2
Revises: c2d3e4f5a6b7
Create Date: 2026-10-26 18:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e7f8a9b0c1d2'
down_revision = 'c2d3e4f5a6b7'
branch_labels = None
depends_on = None


COLUMN_NAMES = ['mcp_transport', 'stdio_command', 'stdio_args', 'stdio_env', 'stdio_cwd']


def _columns():
    # Built fresh per call: a Column object can only be attached to one table
    return [
        sa.Column('mcp_transport', sa.String(20), nullable=True, server_default='http'),
        sa.Column('stdio_command', sa.String(500), nullable=True),
        sa.Column('stdio_args', sa.Text(), nullable=True),
        sa.Column('stdio_env', sa.Text(), nullable=True),
        sa.Column('stdio_cwd', sa.String(500), nullable=True),
    ]


def upgrade():
    # These model columns were never migrated; some databases got them via
    # create_all() or by hand, so only add the ones that are missing.
    existing = {col['name'] for col in sa.inspect(op.get_bind()).get_columns('apps')}
    with op.batch_alter_table('apps', schema=None) as batch_op:
        for column in _columns():
            if column.name not in existing:
                batch_op.add_column(column)


def downgrade():
    with op.batch_alter_table('apps', schema=None) as batch_op:
        for name in reversed(COLUMN_NAMES):
            batch_op.drop_column(name)
