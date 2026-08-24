"""0013_traffic_monitoring

Revision ID: 83572d727947
Revises: 6d761b03016c
Create Date: 2026-07-30 09:50:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '83572d727947'
down_revision: Union[str, Sequence[str], None] = '6d761b03016c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('company_profiles', sa.Column('website_domain', sa.String(), nullable=True))

    op.create_table('traffic_snapshots',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('competitor_id', sa.Integer(), nullable=False),
        sa.Column('domain', sa.String(), nullable=False),
        sa.Column('month', sa.Date(), nullable=False),
        sa.Column('visits', sa.Integer(), nullable=True),
        sa.Column('source', sa.String(), nullable=False),
        sa.Column('fetched_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['competitor_id'], ['competitors.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('competitor_id', 'month', 'source', name='uq_traffic_snapshot_month')
    )
    op.create_index(op.f('ix_traffic_snapshots_id'), 'traffic_snapshots', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_traffic_snapshots_id'), table_name='traffic_snapshots')
    op.drop_table('traffic_snapshots')
    op.drop_column('company_profiles', 'website_domain')
