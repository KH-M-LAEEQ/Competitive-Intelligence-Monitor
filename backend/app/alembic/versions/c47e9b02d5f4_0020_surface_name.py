"""0020_surface_name

Revision ID: c47e9b02d5f4
Revises: 9a1c3f6e2b47
Create Date: 2026-08-24 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c47e9b02d5f4'
down_revision: Union[str, Sequence[str], None] = '9a1c3f6e2b47'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('surfaces', sa.Column('name', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('surfaces', 'name')
