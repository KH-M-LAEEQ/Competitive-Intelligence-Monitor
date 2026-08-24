"""0018_snapshot_summary

Revision ID: d29f4a7c8e12
Revises: b4de719f2a13
Create Date: 2026-08-23 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd29f4a7c8e12'
down_revision: Union[str, Sequence[str], None] = 'b4de719f2a13'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('snapshots', sa.Column('summary', sa.Text(), nullable=True))
    op.add_column('snapshots', sa.Column('highlights', sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column('snapshots', 'highlights')
    op.drop_column('snapshots', 'summary')
