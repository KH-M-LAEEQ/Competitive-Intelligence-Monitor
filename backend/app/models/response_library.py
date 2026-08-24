from datetime import datetime

from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, ForeignKey
from app.base import Base


class ResponseLibraryItem(Base):
    """Reusable, human-authored talk tracks/positioning statements. Direct
    editor/owner CRUD — no approval gate, unlike briefings and battlecard
    updates, since these are manually written by a team member rather than
    LLM-drafted.
    """

    __tablename__ = "response_library_items"

    id = Column(Integer, primary_key=True, index=True)

    workspace_id = Column(
        Integer,
        ForeignKey("workspaces.id"),
        nullable=False
    )

    competitor_id = Column(Integer, ForeignKey("competitors.id"), nullable=True)

    title = Column(String, nullable=False)
    body_markdown = Column(Text, nullable=False)
    tags = Column(JSON, nullable=True)

    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
