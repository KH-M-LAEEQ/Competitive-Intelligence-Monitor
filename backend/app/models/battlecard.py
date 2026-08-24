from datetime import datetime

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from app.base import Base


class Battlecard(Base):
    """The live, currently-approved battlecard for a competitor. Proposed
    changes go through BattlecardUpdate + the approval queue first — this
    row only ever changes via battlecard_service.apply_approved_update().
    """

    __tablename__ = "battlecards"

    id = Column(Integer, primary_key=True, index=True)

    workspace_id = Column(
        Integer,
        ForeignKey("workspaces.id"),
        nullable=False
    )

    competitor_id = Column(
        Integer,
        ForeignKey("competitors.id"),
        nullable=False,
        unique=True
    )

    title = Column(String, nullable=False)
    content_markdown = Column(Text, nullable=False, default="")
    version = Column(Integer, nullable=False, default=0)

    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )
