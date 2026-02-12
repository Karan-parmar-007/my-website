"""Add auth tables and social media

Revision ID: a1b2c3d4e5f6
Revises: d672cf710491
Create Date: 2026-02-04 16:52:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'd672cf710491'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def column_exists(table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table."""
    conn = op.get_bind()
    result = conn.execute(text(f"""
        SELECT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = '{table_name}' AND column_name = '{column_name}'
        )
    """))
    return result.scalar()


def table_exists(table_name: str) -> bool:
    """Check if a table exists."""
    conn = op.get_bind()
    result = conn.execute(text(f"""
        SELECT EXISTS (
            SELECT 1 FROM information_schema.tables 
            WHERE table_name = '{table_name}'
        )
    """))
    return result.scalar()


def upgrade() -> None:
    # ### SignUpLog table ###
    if not table_exists('signuplog'):
        op.create_table('signuplog',
            sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('user_email', sa.VARCHAR(length=255), nullable=False),
            sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_signuplog_user_email'), 'signuplog', ['user_email'], unique=False)
        op.create_index(op.f('ix_signuplog_user_id'), 'signuplog', ['user_id'], unique=False)

    # ### LoginLog table ###
    if not table_exists('loginlog'):
        op.create_table('loginlog',
            sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('user_email', sa.VARCHAR(length=255), nullable=False),
            sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_loginlog_user_email'), 'loginlog', ['user_email'], unique=False)
        op.create_index(op.f('ix_loginlog_user_id'), 'loginlog', ['user_id'], unique=False)

    # ### RefreshToken table ###
    if not table_exists('refreshtoken'):
        op.create_table('refreshtoken',
            sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('token_hash', sa.VARCHAR(length=256), nullable=False),
            sa.Column('expires_at', postgresql.TIMESTAMP(timezone=True), nullable=False),
            sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), nullable=False),
            sa.Column('updated_at', postgresql.TIMESTAMP(timezone=True), nullable=False),
            sa.Column('device_info', sa.VARCHAR(length=500), nullable=True),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_refreshtoken_user_id'), 'refreshtoken', ['user_id'], unique=False)
        op.create_index(op.f('ix_refreshtoken_expires_at'), 'refreshtoken', ['expires_at'], unique=False)

    # ### SocialMedia table ###
    if not table_exists('socialmedia'):
        op.create_table('socialmedia',
            sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('name', sa.VARCHAR(length=50), nullable=False),
            sa.Column('link', sa.VARCHAR(length=500), nullable=False),
            sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), nullable=False),
            sa.Column('updated_at', postgresql.TIMESTAMP(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint('id')
        )
    
    # Drop old social media columns from profileinfo (migrated to separate table)
    if column_exists('profileinfo', 'github_url'):
        op.drop_column('profileinfo', 'github_url')
    if column_exists('profileinfo', 'linkedin_url'):
        op.drop_column('profileinfo', 'linkedin_url')
    if column_exists('profileinfo', 'instagram'):
        op.drop_column('profileinfo', 'instagram')


def downgrade() -> None:
    # ### Drop tables in reverse order ###
    if table_exists('socialmedia'):
        op.drop_table('socialmedia')
    
    if table_exists('refreshtoken'):
        op.drop_index(op.f('ix_refreshtoken_expires_at'), table_name='refreshtoken')
        op.drop_index(op.f('ix_refreshtoken_user_id'), table_name='refreshtoken')
        op.drop_table('refreshtoken')
    
    if table_exists('loginlog'):
        op.drop_index(op.f('ix_loginlog_user_id'), table_name='loginlog')
        op.drop_index(op.f('ix_loginlog_user_email'), table_name='loginlog')
        op.drop_table('loginlog')
    
    if table_exists('signuplog'):
        op.drop_index(op.f('ix_signuplog_user_id'), table_name='signuplog')
        op.drop_index(op.f('ix_signuplog_user_email'), table_name='signuplog')
        op.drop_table('signuplog')
    
    # Re-add social media columns to profileinfo
    if not column_exists('profileinfo', 'github_url'):
        op.add_column('profileinfo', sa.Column('github_url', sa.VARCHAR(length=255), nullable=True))
    if not column_exists('profileinfo', 'linkedin_url'):
        op.add_column('profileinfo', sa.Column('linkedin_url', sa.VARCHAR(length=255), nullable=True))
    if not column_exists('profileinfo', 'instagram'):
        op.add_column('profileinfo', sa.Column('instagram', sa.VARCHAR(length=255), nullable=True))
