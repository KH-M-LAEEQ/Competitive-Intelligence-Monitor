import enum
from datetime import datetime

from sqlalchemy import Column, Integer, String, Text, DateTime, Enum, ForeignKey
from app.base import Base


class ApprovalItemType(str, enum.Enum):
    briefing = "briefing"
    battlecard_update = "battlecard_update"
    crm_note = "crm_note"


class ApprovalStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class ApprovalItem(Base):
    """One unified queue across every kind of thing that needs a human
    sign-off (briefings now, battlecard updates from Phase 8) — the
    approval-queue UI is a single list keyed off `item_type` rather than a
    UNION query across separate approval tables per content type.
    """

    __tablename__ = "approval_items"

    id = Column(Integer, primary_key=True, index=True)

    workspace_id = Column(
        Integer,
        ForeignKey("workspaces.id"),
        nullable=False
    )

    item_type = Column(Enum(ApprovalItemType), nullable=False)
    item_id = Column(Integer, nullable=False)

    status = Column(
        Enum(ApprovalStatus),
        nullable=False,
        default=ApprovalStatus.pending
    )

    requested_at = Column(
        DateTime,
        default=datetime.utcnow
    )

    decided_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    decided_at = Column(DateTime, nullable=True)
    decision_notes = Column(Text, nullable=True)
