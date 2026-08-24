"""0014_own_site

Revision ID: e3fda0653a44
Revises: 83572d727947
Create Date: 2026-07-30 10:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e3fda0653a44'
down_revision: Union[str, Sequence[str], None] = '83572d727947'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'competitors',
        sa.Column('is_own_site', sa.Boolean(), nullable=False, server_default=sa.false())
    )
    op.alter_column('competitors', 'is_own_site', server_default=None)


def downgrade() -> None:
    op.drop_column('competitors', 'is_own_site')
