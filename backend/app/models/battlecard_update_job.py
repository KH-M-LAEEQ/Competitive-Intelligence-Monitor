import enum
from datetime import datetime

from sqlalchemy import Column, Integer, Text, DateTime, JSON, Enum, ForeignKey
from app.base import Base


class BattlecardUpdateJobStatus(str, enum.Enum):
    queued = "queued"
    running = "running"
    success = "success"
    failed = "failed"


class BattlecardUpdateJob(Base):
    """Tracks a background battlecard-update proposal request so the frontend
    can dispatch propose-update and poll for completion instead of blocking
    on the LLM call — see
    services/battlecard_service.py::run_battlecard_update_job().
    """

    __tablename__ = "battlecard_update_jobs"

    id = Column(Integer, primary_key=True, index=True)

    workspace_id = Column(
        Integer,
        ForeignKey("workspaces.id"),
        nullable=False
    )

    competitor_id = Column(
        Integer,
        ForeignKey("competitors.id"),
        nullable=False
    )

    change_log_ids = Column(JSON, nullable=False)

    status = Column(
        Enum(BattlecardUpdateJobStatus),
        nullable=False,
        default=BattlecardUpdateJobStatus.queued
    )

    battlecard_update_id = Column(Integer, ForeignKey("battlecard_updates.id"), nullable=True)
    error = Column(Text, nullable=True)

    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)
