"""0017_change_log_highlights

Revision ID: b4de719f2a13
Revises: a1c7e2f9b301
Create Date: 2026-07-31 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b4de719f2a13'
down_revision: Union[str, Sequence[str], None] = 'a1c7e2f9b301'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('change_logs', sa.Column('highlights', sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column('change_logs', 'highlights')
