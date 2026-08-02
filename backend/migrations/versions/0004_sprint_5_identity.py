"""Create Sprint 5 identity models.

Revision ID: 0004_sprint_5
Revises: 0003_sprint_3
Create Date: 2026-08-02
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0004_sprint_5"
down_revision: str | None = "0003_sprint_3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # user role enum
    sa.Enum('FARMER', 'OFFICER', 'AGRONOMIST', 'ADMIN', 'SYSTEM', name='userrole').create(op.get_bind())

    # Create user table
    op.create_table(
        'user',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('uuid', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('phone', sa.String(length=15), nullable=True),
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.Column('password_hash', sa.String(length=200), nullable=False, comment='Argon2id hash — never logged or returned via API'),
        sa.Column('role', sa.String(length=20), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('is_verified', sa.Boolean(), nullable=False),
        sa.Column('last_login', sa.DateTime(timezone=True), nullable=True),
        sa.Column('farmer_profile_id', sa.Integer(), nullable=True),
        sa.Column('officer_profile_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['farmer_profile_id'], ['farmer.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['officer_profile_id'], ['officer.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_user_uuid'), 'user', ['uuid'], unique=True)
    op.create_index(op.f('ix_user_phone'), 'user', ['phone'], unique=True)
    op.create_index(op.f('ix_user_email'), 'user', ['email'], unique=True)
    op.create_index(op.f('ix_user_farmer_profile_id'), 'user', ['farmer_profile_id'], unique=True)
    op.create_index(op.f('ix_user_officer_profile_id'), 'user', ['officer_profile_id'], unique=True)
    op.create_index('ix_user_role_active', 'user', ['role', 'is_active'], unique=False)

    # Create refresh_token table
    op.create_table(
        'refresh_token',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('jti', postgresql.UUID(as_uuid=True), nullable=False, comment='JWT ID — uniquely identifies this token for revocation'),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('issued_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True, comment='Null means the token is still valid'),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_refresh_token_jti'), 'refresh_token', ['jti'], unique=True)
    op.create_index(op.f('ix_refresh_token_user_id'), 'refresh_token', ['user_id'], unique=False)
    op.create_index(op.f('ix_refresh_token_expires_at'), 'refresh_token', ['expires_at'], unique=False)
    op.create_index('ix_refresh_token_user_active', 'refresh_token', ['user_id', 'revoked_at'], unique=False)


def downgrade() -> None:
    op.drop_table('refresh_token')
    op.drop_table('user')
    sa.Enum('FARMER', 'OFFICER', 'AGRONOMIST', 'ADMIN', 'SYSTEM', name='userrole').drop(op.get_bind())
