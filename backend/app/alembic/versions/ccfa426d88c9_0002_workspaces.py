"""0002_workspaces

Revision ID: ccfa426d88c9
Revises: 8c785b33b579
Create Date: 2026-07-30 01:13:42.265611

"""
import re
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ccfa426d88c9'
down_revision: Union[str, Sequence[str], None] = '8c785b33b579'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _slugify(email: str, seen: set[str]) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", email.lower()).strip("-") or "workspace"
    slug = base
    n = 2
    while slug in seen:
        slug = f"{base}-{n}"
        n += 1
    seen.add(slug)
    return slug


def upgrade() -> None:
    op.create_table('workspaces',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('slug', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_workspaces_id'), 'workspaces', ['id'], unique=False)
    op.create_index(op.f('ix_workspaces_slug'), 'workspaces', ['slug'], unique=True)

    op.create_table('workspace_members',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('workspace_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('role', sa.Enum('owner', 'editor', 'reviewer', name='workspacerole'), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('workspace_id', 'user_id', name='uq_workspace_member')
    )
    op.create_index(op.f('ix_workspace_members_id'), 'workspace_members', ['id'], unique=False)

    # Rename competitors.user_id -> created_by_user_id (preserves existing FK data).
    op.alter_column('competitors', 'user_id', new_column_name='created_by_user_id')

    op.add_column('competitors', sa.Column('workspace_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_competitors_workspace_id', 'competitors', 'workspaces', ['workspace_id'], ['id']
    )

    # --- Data backfill: one owner Workspace per existing User ---
    bind = op.get_bind()

    workspaces_t = sa.table(
        'workspaces',
        sa.column('id', sa.Integer),
        sa.column('name', sa.String),
        sa.column('slug', sa.String),
    )
    members_t = sa.table(
        'workspace_members',
        sa.column('workspace_id', sa.Integer),
        sa.column('user_id', sa.Integer),
        sa.column('role', sa.String),
    )
    competitors_t = sa.table(
        'competitors',
        sa.column('workspace_id', sa.Integer),
        sa.column('created_by_user_id', sa.Integer),
    )

    users = bind.execute(sa.text("SELECT id, email, full_name FROM users")).fetchall()
    seen_slugs: set[str] = set()
    user_to_workspace: dict[int, int] = {}

    for user_id, email, full_name in users:
        slug = _slugify(email, seen_slugs)
        name = f"{full_name}'s Workspace" if full_name else f"{email}'s Workspace"
        result = bind.execute(
            workspaces_t.insert().values(name=name, slug=slug).returning(workspaces_t.c.id)
        )
        workspace_id = result.scalar_one()
        user_to_workspace[user_id] = workspace_id

        bind.execute(
            members_t.insert().values(
                workspace_id=workspace_id, user_id=user_id, role='owner'
            )
        )

    for user_id, workspace_id in user_to_workspace.items():
        bind.execute(
            competitors_t.update()
            .where(competitors_t.c.created_by_user_id == user_id)
            .values(workspace_id=workspace_id)
        )

    op.alter_column('competitors', 'workspace_id', nullable=False)


def downgrade() -> None:
    op.drop_constraint('fk_competitors_workspace_id', 'competitors', type_='foreignkey')
    op.drop_column('competitors', 'workspace_id')
    op.alter_column('competitors', 'created_by_user_id', new_column_name='user_id')

    op.drop_index(op.f('ix_workspace_members_id'), table_name='workspace_members')
    op.drop_table('workspace_members')
    sa.Enum(name='workspacerole').drop(op.get_bind(), checkfirst=True)
    op.drop_index(op.f('ix_workspaces_slug'), table_name='workspaces')
    op.drop_index(op.f('ix_workspaces_id'), table_name='workspaces')
    op.drop_table('workspaces')
