"""0021_battlecard_update_jobs

Revision ID: a7e3f6d4c9b2
Revises: 9f97deb010d8
Create Date: 2026-08-29 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a7e3f6d4c9b2'
down_revision: Union[str, Sequence[str], None] = '9f97deb010d8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'battlecard_update_jobs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('workspace_id', sa.Integer(), nullable=False),
        sa.Column('competitor_id', sa.Integer(), nullable=False),
        sa.Column('change_log_ids', sa.JSON(), nullable=False),
        sa.Column(
            'status',
            sa.Enum('queued', 'running', 'success', 'failed', name='battlecardupdatejobstatus'),
            nullable=False,
        ),
        sa.Column('battlecard_update_id', sa.Integer(), nullable=True),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('created_by_user_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('finished_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['battlecard_update_id'], ['battlecard_updates.id'], ),
        sa.ForeignKeyConstraint(['competitor_id'], ['competitors.id'], ),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_battlecard_update_jobs_id'), 'battlecard_update_jobs', ['id'], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f('ix_battlecard_update_jobs_id'), table_name='battlecard_update_jobs')
    op.drop_table('battlecard_update_jobs')
    sa.Enum(name='battlecardupdatejobstatus').drop(op.get_bind(), checkfirst=True)
