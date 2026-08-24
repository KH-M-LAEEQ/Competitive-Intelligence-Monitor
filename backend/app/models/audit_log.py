from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, JSON, ForeignKey
from app.base import Base


class AuditLog(Base):
    """Records every approval decision (who approved/rejected what, when).
    Scoped to the approval flow for now, the piece the docx spec calls out
    explicitly ("who approved what, when") — wiring every other router's
    mutations into this table is a straightforward fast-follow, not done
    here to keep this phase's surface area focused.
    """

    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)

    workspace_id = Column(
        Integer,
        ForeignKey("workspaces.id"),
        nullable=False
    )

    actor_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    action = Column(String, nullable=False)
    entity_type = Column(String, nullable=False)
    entity_id = Column(Integer, nullable=True)

    extra_data = Column(JSON, nullable=True)

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )
