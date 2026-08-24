"""0019_structured_change_items

Revision ID: 9a1c3f6e2b47
Revises: d29f4a7c8e12
Create Date: 2026-08-23 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9a1c3f6e2b47'
down_revision: Union[str, Sequence[str], None] = 'd29f4a7c8e12'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('change_logs', sa.Column('headline', sa.String(), nullable=True))
    op.add_column('change_logs', sa.Column('items', sa.JSON(), nullable=True))
    op.add_column('snapshots', sa.Column('headline', sa.String(), nullable=True))
    op.add_column('snapshots', sa.Column('facts', sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column('snapshots', 'facts')
    op.drop_column('snapshots', 'headline')
    op.drop_column('change_logs', 'items')
    op.drop_column('change_logs', 'headline')
