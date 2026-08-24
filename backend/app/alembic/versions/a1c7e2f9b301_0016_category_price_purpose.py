"""0016_category_price_purpose

Revision ID: a1c7e2f9b301
Revises: 0bb83c528d02
Create Date: 2026-07-30 20:40:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'a1c7e2f9b301'
down_revision: Union[str, Sequence[str], None] = '0bb83c528d02'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE llmusagepurpose ADD VALUE IF NOT EXISTS 'category_price'")


def downgrade() -> None:
    # Same pragmatic no-op tradeoff as 0015's downgrade — Postgres has no
    # ADD VALUE ... IF NOT EXISTS counterpart for removing an enum value.
    pass
