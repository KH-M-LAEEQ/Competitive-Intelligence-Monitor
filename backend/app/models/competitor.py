from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey
from app.base import Base


class Competitor(Base):
    __tablename__ = "competitors"

    id = Column(Integer, primary_key=True, index=True)

    workspace_id = Column(
        Integer,
        ForeignKey("workspaces.id"),
        nullable=False
    )

    created_by_user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False
    )

    name = Column(
        String,
        nullable=False
    )

    # Marks the single, hidden "this is us" competitor used as the
    # comparison benchmark (see own_site_service.py) — at most one per
    # workspace, enforced in that service rather than a DB constraint.
    # Excluded from the normal competitors list/add-flow.
    is_own_site = Column(
        Boolean,
        nullable=False,
        default=False
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )