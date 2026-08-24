import enum
from datetime import datetime

from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Enum, ForeignKey, Table
)
from app.base import Base


class BriefingAudience(str, enum.Enum):
    exec = "exec"
    sales = "sales"
    product = "product"
    all = "all"


class BriefingDigestType(str, enum.Enum):
    urgent = "urgent"
    daily = "daily"
    weekly = "weekly"


class BriefingStatus(str, enum.Enum):
    draft = "draft"
    pending_approval = "pending_approval"
    approved = "approved"
    rejected = "rejected"
    delivered = "delivered"


briefing_change_logs = Table(
    "briefing_change_logs",
    Base.metadata,
    Column("briefing_id", Integer, ForeignKey("briefings.id"), primary_key=True),
    Column("change_log_id", Integer, ForeignKey("change_logs.id"), primary_key=True),
)


class Briefing(Base):
    __tablename__ = "briefings"

    id = Column(Integer, primary_key=True, index=True)

    workspace_id = Column(
        Integer,
        ForeignKey("workspaces.id"),
        nullable=False
    )

    audience = Column(
        Enum(BriefingAudience),
        nullable=False,
        default=BriefingAudience.all
    )

    digest_type = Column(
        Enum(BriefingDigestType),
        nullable=False,
        default=BriefingDigestType.urgent
    )

    title = Column(String, nullable=False)
    body_markdown = Column(Text, nullable=False)

    status = Column(
        Enum(BriefingStatus),
        nullable=False,
        default=BriefingStatus.draft
    )

    generated_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    decided_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    decided_at = Column(DateTime, nullable=True)
    delivered_at = Column(DateTime, nullable=True)

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )
