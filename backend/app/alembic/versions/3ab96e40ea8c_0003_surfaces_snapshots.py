"""0003_surfaces_snapshots

Revision ID: 3ab96e40ea8c
Revises: ccfa426d88c9
Create Date: 2026-07-30 01:19:12.766639

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '3ab96e40ea8c'
down_revision: Union[str, Sequence[str], None] = 'ccfa426d88c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('surfaces',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('competitor_id', sa.Integer(), nullable=False),
        sa.Column('surface_type', sa.Enum('pricing', 'product', 'changelog', 'blog', 'jobs', 'other', name='surfacetype'), nullable=False),
        sa.Column('url', sa.String(), nullable=False),
        sa.Column('check_frequency', sa.String(), nullable=True),
        sa.Column('capture_visual', sa.Boolean(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('last_checked_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['competitor_id'], ['competitors.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_surfaces_id'), 'surfaces', ['id'], unique=False)

    op.create_table('snapshots',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('surface_id', sa.Integer(), nullable=False),
        sa.Column('text_content', sa.Text(), nullable=True),
        sa.Column('content_hash', sa.String(), nullable=True),
        sa.Column('screenshot_path', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['surface_id'], ['surfaces.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_snapshots_content_hash'), 'snapshots', ['content_hash'], unique=False)
    op.create_index(op.f('ix_snapshots_id'), 'snapshots', ['id'], unique=False)

    op.add_column('change_logs', sa.Column('surface_id', sa.Integer(), nullable=True))
    op.add_column('change_logs', sa.Column('old_snapshot_id', sa.Integer(), nullable=True))
    op.add_column('change_logs', sa.Column('new_snapshot_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_change_logs_new_snapshot_id', 'change_logs', 'snapshots', ['new_snapshot_id'], ['id']
    )
    op.create_foreign_key(
        'fk_change_logs_old_snapshot_id', 'change_logs', 'snapshots', ['old_snapshot_id'], ['id']
    )
    op.create_foreign_key(
        'fk_change_logs_surface_id', 'change_logs', 'surfaces', ['surface_id'], ['id']
    )

    op.add_column('competitors', sa.Column('created_at', sa.DateTime(), nullable=True))

    # --- Data backfill: one 'pricing' Surface per existing Competitor,
    # carrying its url/check_frequency/last_snapshot forward. ---
    bind = op.get_bind()

    surfaces_t = sa.table(
        'surfaces',
        sa.column('id', sa.Integer),
        sa.column('competitor_id', sa.Integer),
        sa.column('surface_type', sa.String),
        sa.column('url', sa.String),
        sa.column('check_frequency', sa.String),
        sa.column('capture_visual', sa.Boolean),
        sa.column('is_active', sa.Boolean),
    )
    snapshots_t = sa.table(
        'snapshots',
        sa.column('id', sa.Integer),
        sa.column('surface_id', sa.Integer),
        sa.column('text_content', sa.Text),
    )
    change_logs_t = sa.table(
        'change_logs',
        sa.column('id', sa.Integer),
        sa.column('competitor_id', sa.Integer),
        sa.column('surface_id', sa.Integer),
        sa.column('old_snapshot_id', sa.Integer),
        sa.column('new_snapshot_id', sa.Integer),
    )

    competitors = bind.execute(
        sa.text("SELECT id, url, check_frequency, last_snapshot FROM competitors")
    ).fetchall()

    competitor_to_surface: dict[int, int] = {}
    surface_to_latest_snapshot: dict[int, int] = {}

    for competitor_id, url, check_frequency, last_snapshot in competitors:
        result = bind.execute(
            surfaces_t.insert().values(
                competitor_id=competitor_id,
                surface_type='pricing',
                url=url,
                check_frequency=check_frequency,
                capture_visual=False,
                is_active=True,
            ).returning(surfaces_t.c.id)
        )
        surface_id = result.scalar_one()
        competitor_to_surface[competitor_id] = surface_id

        if last_snapshot is not None:
            snap_result = bind.execute(
                snapshots_t.insert().values(
                    surface_id=surface_id, text_content=last_snapshot
                ).returning(snapshots_t.c.id)
            )
            surface_to_latest_snapshot[surface_id] = snap_result.scalar_one()

    change_logs = bind.execute(
        sa.text("SELECT id, competitor_id, old_snapshot, new_snapshot FROM change_logs")
    ).fetchall()

    for change_log_id, competitor_id, old_snapshot_text, new_snapshot_text in change_logs:
        surface_id = competitor_to_surface[competitor_id]

        old_snapshot_id = None
        if old_snapshot_text is not None:
            old_snapshot_id = bind.execute(
                snapshots_t.insert().values(
                    surface_id=surface_id, text_content=old_snapshot_text
                ).returning(snapshots_t.c.id)
            ).scalar_one()

        new_snapshot_id = bind.execute(
            snapshots_t.insert().values(
                surface_id=surface_id, text_content=new_snapshot_text
            ).returning(snapshots_t.c.id)
        ).scalar_one()

        bind.execute(
            change_logs_t.update()
            .where(change_logs_t.c.id == change_log_id)
            .values(
                surface_id=surface_id,
                old_snapshot_id=old_snapshot_id,
                new_snapshot_id=new_snapshot_id,
            )
        )

    op.alter_column('change_logs', 'surface_id', nullable=False)
    op.alter_column('change_logs', 'new_snapshot_id', nullable=False)

    op.drop_column('change_logs', 'old_snapshot')
    op.drop_column('change_logs', 'new_snapshot')

    op.drop_column('competitors', 'url')
    op.drop_column('competitors', 'check_frequency')
    op.drop_column('competitors', 'last_checked_at')
    op.drop_column('competitors', 'last_snapshot')


def downgrade() -> None:
    op.add_column('competitors', sa.Column('last_snapshot', sa.TEXT(), autoincrement=False, nullable=True))
    op.add_column('competitors', sa.Column('last_checked_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=True))
    op.add_column('competitors', sa.Column('check_frequency', sa.VARCHAR(), autoincrement=False, nullable=True))
    op.add_column('competitors', sa.Column('url', sa.VARCHAR(), autoincrement=False, nullable=True))
    op.add_column('change_logs', sa.Column('new_snapshot', sa.TEXT(), autoincrement=False, nullable=True))
    op.add_column('change_logs', sa.Column('old_snapshot', sa.TEXT(), autoincrement=False, nullable=True))

    bind = op.get_bind()
    bind.execute(sa.text("""
        UPDATE competitors c
        SET url = s.url, check_frequency = s.check_frequency, last_checked_at = s.last_checked_at
        FROM surfaces s
        WHERE s.competitor_id = c.id
    """))
    bind.execute(sa.text("""
        UPDATE competitors c
        SET last_snapshot = snap.text_content
        FROM surfaces s
        JOIN snapshots snap ON snap.surface_id = s.id
        WHERE s.competitor_id = c.id
        AND snap.id = (SELECT max(id) FROM snapshots WHERE surface_id = s.id)
    """))
    bind.execute(sa.text("""
        UPDATE change_logs cl
        SET new_snapshot = new_snap.text_content
        FROM snapshots new_snap
        WHERE new_snap.id = cl.new_snapshot_id
    """))
    bind.execute(sa.text("""
        UPDATE change_logs cl
        SET old_snapshot = old_snap.text_content
        FROM snapshots old_snap
        WHERE old_snap.id = cl.old_snapshot_id
    """))

    op.alter_column('competitors', 'url', nullable=False)

    op.drop_constraint('fk_change_logs_surface_id', 'change_logs', type_='foreignkey')
    op.drop_constraint('fk_change_logs_old_snapshot_id', 'change_logs', type_='foreignkey')
    op.drop_constraint('fk_change_logs_new_snapshot_id', 'change_logs', type_='foreignkey')
    op.drop_column('change_logs', 'new_snapshot_id')
    op.drop_column('change_logs', 'old_snapshot_id')
    op.drop_column('change_logs', 'surface_id')
    op.drop_column('competitors', 'created_at')

    op.drop_index(op.f('ix_snapshots_id'), table_name='snapshots')
    op.drop_index(op.f('ix_snapshots_content_hash'), table_name='snapshots')
    op.drop_table('snapshots')
    op.drop_index(op.f('ix_surfaces_id'), table_name='surfaces')
    op.drop_table('surfaces')
    sa.Enum(name='surfacetype').drop(op.get_bind(), checkfirst=True)
