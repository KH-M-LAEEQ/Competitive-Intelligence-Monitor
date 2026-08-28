"""0019_briefing_jobs

Revision ID: 9f97deb010d8
Revises: c47e9b02d5f4
Create Date: 2026-08-28 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '9f97deb010d8'
down_revision: Union[str, Sequence[str], None] = 'c47e9b02d5f4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'briefing_jobs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('workspace_id', sa.Integer(), nullable=False),
        # audience/digest_type reuse the existing 'briefingaudience' /
        # 'briefingdigesttype' Postgres enum types created alongside the
        # briefings table — create_type=False so this doesn't try to
        # recreate them.
        sa.Column(
            'audience',
            postgresql.ENUM('exec', 'sales', 'product', 'all', name='briefingaudience', create_type=False),
            nullable=False,
        ),
        sa.Column(
            'digest_type',
            postgresql.ENUM('urgent', 'daily', 'weekly', name='briefingdigesttype', create_type=False),
            nullable=False,
        ),
        sa.Column('change_log_ids', sa.JSON(), nullable=False),
        sa.Column(
            'status',
            sa.Enum('queued', 'running', 'success', 'failed', name='briefingjobstatus'),
            nullable=False,
        ),
        sa.Column('briefing_id', sa.Integer(), nullable=True),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('created_by_user_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('finished_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['briefing_id'], ['briefings.id'], ),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_briefing_jobs_id'), 'briefing_jobs', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_briefing_jobs_id'), table_name='briefing_jobs')
    op.drop_table('briefing_jobs')
    sa.Enum(name='briefingjobstatus').drop(op.get_bind(), checkfirst=True)
