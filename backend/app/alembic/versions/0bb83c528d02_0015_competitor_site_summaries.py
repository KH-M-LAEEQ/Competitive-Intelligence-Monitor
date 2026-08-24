"""0015_competitor_site_summaries

Revision ID: 0bb83c528d02
Revises: e3fda0653a44
Create Date: 2026-07-30 12:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0bb83c528d02'
down_revision: Union[str, Sequence[str], None] = 'e3fda0653a44'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Postgres 12+ allows ADD VALUE outside of a transaction that also uses
    # the new value — safe here since nothing in this migration inserts a
    # row with it.
    op.execute("ALTER TYPE llmusagepurpose ADD VALUE IF NOT EXISTS 'site_summary'")

    op.create_table('competitor_site_summaries',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('competitor_id', sa.Integer(), nullable=False),
        sa.Column('categories', sa.JSON(), nullable=True),
        sa.Column('current_offers', sa.JSON(), nullable=True),
        sa.Column('generated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['competitor_id'], ['competitors.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('competitor_id')
    )
    op.create_index(
        op.f('ix_competitor_site_summaries_id'), 'competitor_site_summaries', ['id'], unique=False
    )


def downgrade() -> None:
    op.drop_index(
        op.f('ix_competitor_site_summaries_id'), table_name='competitor_site_summaries'
    )
    op.drop_table('competitor_site_summaries')

    # Postgres has no ADD VALUE ... IF NOT EXISTS counterpart for removing
    # one — reversing it cleanly means rebuilding the enum type (rename,
    # recreate without the value, repoint the column, drop the old type),
    # which is disproportionate for a value that's harmless to leave behind.
    # Left as a no-op, same pragmatic tradeoff already accepted elsewhere in
    # this migration history for hard-to-reverse enum changes.
