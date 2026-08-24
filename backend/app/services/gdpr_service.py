from datetime import datetime

from sqlalchemy.orm import Session

from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMember, WorkspaceRole
from app.models.competitor import Competitor
from app.models.response_library import ResponseLibraryItem
from app.models.briefing import Briefing
from app.models.battlecard_update import BattlecardUpdate
from app.models.approval_item import ApprovalItem
from app.models.audit_log import AuditLog

__all__ = ["export_user_data", "delete_user_account", "SoleOwnerWithOthersError"]


class SoleOwnerWithOthersError(Exception):
    """Raised when the account can't be deleted because it's the only owner
    of a workspace that still has other members — deleting it would leave
    that workspace's remaining members without anyone able to manage it.
    Transferring ownership first is a decision for the user to make
    explicitly, not something this endpoint should do silently.
    """
    pass


def export_user_data(db: Session, user: User) -> dict:
    """A GDPR-style personal data export. Scoped to data that identifies or
    was authored by this specific user — not the shared workspace content
    (competitors, change logs, etc.) itself, since that belongs to the
    workspace and its other members, not to any one individual.
    """

    memberships = (
        db.query(WorkspaceMember, Workspace.name)
        .join(Workspace, WorkspaceMember.workspace_id == Workspace.id)
        .filter(WorkspaceMember.user_id == user.id)
        .all()
    )

    competitors_created = (
        db.query(Competitor)
        .filter(Competitor.created_by_user_id == user.id)
        .all()
    )

    response_library_items = (
        db.query(ResponseLibraryItem)
        .filter(ResponseLibraryItem.created_by_user_id == user.id)
        .all()
    )

    briefings_generated = (
        db.query(Briefing)
        .filter(Briefing.generated_by_user_id == user.id)
        .all()
    )

    battlecard_updates_authored = (
        db.query(BattlecardUpdate)
        .filter(BattlecardUpdate.created_by_user_id == user.id)
        .all()
    )

    approval_decisions = (
        db.query(ApprovalItem)
        .filter(ApprovalItem.decided_by == user.id)
        .all()
    )

    audit_entries = (
        db.query(AuditLog)
        .filter(AuditLog.actor_user_id == user.id)
        .all()
    )

    return {
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
        },
        "workspace_memberships": [
            {
                "workspace_id": m.workspace_id,
                "workspace_name": workspace_name,
                "role": m.role.value,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m, workspace_name in memberships
        ],
        "competitors_created": [
            {"id": c.id, "workspace_id": c.workspace_id, "name": c.name,
             "created_at": c.created_at.isoformat() if c.created_at else None}
            for c in competitors_created
        ],
        "response_library_items_authored": [
            {"id": r.id, "workspace_id": r.workspace_id, "title": r.title,
             "created_at": r.created_at.isoformat() if r.created_at else None}
            for r in response_library_items
        ],
        "briefings_generated": [
            {"id": b.id, "workspace_id": b.workspace_id, "title": b.title, "status": b.status.value,
             "created_at": b.created_at.isoformat() if b.created_at else None}
            for b in briefings_generated
        ],
        "battlecard_updates_authored": [
            {"id": bu.id, "workspace_id": bu.workspace_id, "change_summary": bu.change_summary,
             "created_at": bu.created_at.isoformat() if bu.created_at else None}
            for bu in battlecard_updates_authored
        ],
        "approval_decisions_made": [
            {"id": a.id, "workspace_id": a.workspace_id, "item_type": a.item_type.value,
             "status": a.status.value,
             "decided_at": a.decided_at.isoformat() if a.decided_at else None}
            for a in approval_decisions
        ],
        "audit_log_entries": [
            {"id": a.id, "workspace_id": a.workspace_id, "action": a.action,
             "entity_type": a.entity_type, "entity_id": a.entity_id,
             "created_at": a.created_at.isoformat() if a.created_at else None}
            for a in audit_entries
        ],
    }


def delete_user_account(db: Session, user: User) -> None:
    """Anonymizes the account rather than hard-deleting the User row.
    Hard-deleting would either cascade-fail on every FK that still points at
    this user's id across shared workspace content (competitors created,
    briefings generated, approval decisions, audit trail — all of which
    belong to the workspace and its other members too, not just this
    person), or silently orphan those references. Anonymizing the
    personally-identifying fields (email, password, name) while leaving the
    row's id intact satisfies "forget me" without breaking referential
    integrity for content other people still rely on.

    Blocks if this user is the sole owner of a workspace that has other
    members — see SoleOwnerWithOthersError.
    """

    memberships = (
        db.query(WorkspaceMember)
        .filter(WorkspaceMember.user_id == user.id)
        .all()
    )

    for membership in memberships:
        if membership.role != WorkspaceRole.owner:
            continue

        other_owners = (
            db.query(WorkspaceMember)
            .filter(
                WorkspaceMember.workspace_id == membership.workspace_id,
                WorkspaceMember.role == WorkspaceRole.owner,
                WorkspaceMember.user_id != user.id,
            )
            .count()
        )
        other_members = (
            db.query(WorkspaceMember)
            .filter(
                WorkspaceMember.workspace_id == membership.workspace_id,
                WorkspaceMember.user_id != user.id,
            )
            .count()
        )

        if other_owners == 0 and other_members > 0:
            raise SoleOwnerWithOthersError(
                f"You are the only owner of workspace {membership.workspace_id}, "
                "which still has other members. Transfer ownership before "
                "deleting your account."
            )

    for membership in memberships:
        db.delete(membership)

    user.email = f"deleted-user-{user.id}@deleted.local"
    user.full_name = None
    user.hashed_password = f"deleted:{datetime.utcnow().isoformat()}"

    db.commit()
