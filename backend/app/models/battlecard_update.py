from datetime import datetime

from sqlalchemy import Column, Integer, Text, DateTime, JSON, Enum, ForeignKey
from app.base import Base
from app.models.approval_item import ApprovalStatus


class BattlecardUpdate(Base):
    """A proposed revision to a Battlecard, routed through the same
    ApprovalItem queue as briefings (item_type='battlecard_update'). Only
    applied to the live Battlecard once approved — see
    services/battlecard_service.py::apply_approved_update().
    """

    __tablename__ = "battlecard_updates"

    id = Column(Integer, primary_key=True, index=True)

    workspace_id = Column(
        Integer,
        ForeignKey("workspaces.id"),
        nullable=False
    )

    battlecard_id = Column(
        Integer,
        ForeignKey("battlecards.id"),
        nullable=False
    )

    proposed_content_markdown = Column(Text, nullable=False)
    change_summary = Column(Text, nullable=True)
    source_change_log_ids = Column(JSON, nullable=True)

    status = Column(
        Enum(ApprovalStatus),
        nullable=False,
        default=ApprovalStatus.pending
    )

    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    decided_at = Column(DateTime, nullable=True)
