"""add_hierarchical_access_control

Revision ID: ad33b08ca7d7
Revises: c8c9d39f9c78
Create Date: 2025-12-02 01:06:43.235281

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'ad33b08ca7d7'
down_revision = 'c8c9d39f9c78'
branch_labels = None
depends_on = None


PERMISSION_LEVEL_CHECK = (
    "(mcp_service_id IS NOT NULL AND app_id IS NULL AND capability_id IS NULL) OR "
    "(mcp_service_id IS NULL AND app_id IS NOT NULL AND capability_id IS NULL) OR "
    "(mcp_service_id IS NULL AND app_id IS NULL AND capability_id IS NOT NULL)"
)


def upgrade():
    # 1. Add access_control column to mcp_services (default: restricted)
    op.add_column('mcp_services', sa.Column('access_control', sa.String(20), nullable=False, server_default='restricted'))
    
    # 2. Add access_control column to apps (default: public)
    op.add_column('apps', sa.Column('access_control', sa.String(20), nullable=False, server_default='public'))
    
    # 3. Add access_control column to capabilities (default: public)
    op.add_column('capabilities', sa.Column('access_control', sa.String(20), nullable=False, server_default='public'))
    
    # Batch mode issues plain ALTER statements on PostgreSQL and rebuilds the table on
    # SQLite, which cannot add foreign keys or CHECK constraints to an existing table.
    with op.batch_alter_table('account_permissions', schema=None) as batch_op:
        # 4. Add mcp_service_id to account_permissions
        batch_op.add_column(sa.Column('mcp_service_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key('fk_account_permissions_mcp_service', 'mcp_services', ['mcp_service_id'], ['id'])
        
        # 5. Add app_id to account_permissions
        batch_op.add_column(sa.Column('app_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key('fk_account_permissions_app', 'apps', ['app_id'], ['id'])
        
        # 6. Make capability_id nullable (previously required)
        batch_op.alter_column('capability_id',
               existing_type=sa.Integer(),
               nullable=True)
        
        # 7. Add CHECK constraint: exactly one of mcp_service_id, app_id, or capability_id must be set
        batch_op.create_check_constraint('chk_exactly_one_permission_level', PERMISSION_LEVEL_CHECK)


def downgrade():
    with op.batch_alter_table('account_permissions', schema=None) as batch_op:
        # Remove CHECK constraint
        batch_op.drop_constraint('chk_exactly_one_permission_level', type_='check')
        
        # Remove foreign keys and columns from account_permissions
        batch_op.drop_constraint('fk_account_permissions_app', type_='foreignkey')
        batch_op.drop_column('app_id')
        
        batch_op.drop_constraint('fk_account_permissions_mcp_service', type_='foreignkey')
        batch_op.drop_column('mcp_service_id')
        
        # Restore capability_id as NOT NULL
        batch_op.alter_column('capability_id',
               existing_type=sa.Integer(),
               nullable=False)
    
    # Remove access_control columns
    op.drop_column('capabilities', 'access_control')
    op.drop_column('apps', 'access_control')
    op.drop_column('mcp_services', 'access_control')
