import logging
from datetime import datetime
from typing import Literal

from sqlalchemy.orm import Session

from app.models.approval_item import ApprovalItem, ApprovalItemType, ApprovalStatus
from app.models.briefing import Briefing, BriefingStatus
from app.models.battlecard_update import BattlecardUpdate
from app.models.audit_log import AuditLog
from app.services.battlecard_service import apply_approved_update
from app.services.delivery.delivery_service import deliver as deliver_briefing

__all__ = ["decide", "ApprovalItemNotFound", "ApprovalAlreadyDecided"]

logger = logging.getLogger(__name__)


class ApprovalItemNotFound(Exception):
    pass


class ApprovalAlreadyDecided(Exception):
    pass


def decide(
    db: Session,
    workspace_id: int,
    approval_item_id: int,
    decision: Literal["approved", "rejected"],
    actor_user_id: int,
    notes: str | None = None,
) -> ApprovalItem:
    """The only place an ApprovalItem's status is allowed to change from
    'pending' — every draft (briefing now, battlecard update from Phase 8)
    routes through here, and delivery (Phase 9) only ever fires from the
    approval branch below. No other code path may deliver anything.
    """

    approval_item = (
        db.query(ApprovalItem)
        .filter(
            ApprovalItem.id == approval_item_id,
            ApprovalItem.workspace_id == workspace_id
        )
        .first()
    )
    if approval_item is None:
        raise ApprovalItemNotFound()

    if approval_item.status != ApprovalStatus.pending:
        raise ApprovalAlreadyDecided()

    approval_item.status = ApprovalStatus(decision)
    approval_item.decided_by = actor_user_id
    approval_item.decided_at = datetime.utcnow()
    approval_item.decision_notes = notes

    _apply_decision_to_item(db, approval_item)

    db.add(AuditLog(
        workspace_id=workspace_id,
        actor_user_id=actor_user_id,
        action=f"approval.{decision}",
        entity_type=approval_item.item_type.value,
        entity_id=approval_item.item_id,
        extra_data={"notes": notes} if notes else None,
    ))

    db.commit()
    db.refresh(approval_item)

    if decision == "approved":
        # The approval decision itself is already durably committed above —
        # a delivery-layer failure (a flaky connector, a DB hiccup inside
        # deliver_briefing's own commit) must not surface as a 500 on an
        # approval that actually succeeded, and must not leave the session
        # broken for the caller. Delivery failures are still visible via
        # the AuditLog entries deliver_briefing itself writes on the
        # success/failure path; this is only the backstop for the
        # unexpected case.
        try:
            deliver_briefing(db, approval_item)
        except Exception as exc:  # noqa: BLE001 — deliberately broad, see docstring
            logger.warning(
                "Delivery failed after approval of item %s: %s", approval_item.id, exc
            )
            db.rollback()

    return approval_item


def _apply_decision_to_item(db: Session, approval_item: ApprovalItem) -> None:
    if approval_item.item_type == ApprovalItemType.briefing:
        briefing = db.query(Briefing).filter(Briefing.id == approval_item.item_id).first()
        if briefing is None:
            return

        briefing.status = (
            BriefingStatus.approved if approval_item.status == ApprovalStatus.approved
            else BriefingStatus.rejected
        )
        briefing.decided_by_user_id = approval_item.decided_by
        briefing.decided_at = approval_item.decided_at

    elif approval_item.item_type == ApprovalItemType.battlecard_update:
        update = (
            db.query(BattlecardUpdate)
            .filter(BattlecardUpdate.id == approval_item.item_id)
            .first()
        )
        if update is None:
            return

        if approval_item.status == ApprovalStatus.approved:
            apply_approved_update(db, update)
        else:
            update.status = ApprovalStatus.rejected
            update.decided_at = approval_item.decided_at
