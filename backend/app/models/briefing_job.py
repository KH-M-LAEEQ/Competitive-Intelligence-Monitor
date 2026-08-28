import enum
from datetime import datetime

from sqlalchemy import Column, Integer, Text, DateTime, JSON, Enum, ForeignKey
from app.base import Base
from app.models.briefing import BriefingAudience, BriefingDigestType


class BriefingJobStatus(str, enum.Enum):
    queued = "queued"
    running = "running"
    success = "success"
    failed = "failed"


class BriefingJob(Base):
    """Tracks a background briefing-generation request so the frontend can
    dispatch generate-now and poll for completion instead of blocking on
    the LLM call — see services/briefing_service.py::run_briefing_job().
    """

    __tablename__ = "briefing_jobs"

    id = Column(Integer, primary_key=True, index=True)

    workspace_id = Column(
        Integer,
        ForeignKey("workspaces.id"),
        nullable=False
    )

    audience = Column(Enum(BriefingAudience), nullable=False)
    digest_type = Column(Enum(BriefingDigestType), nullable=False)
    change_log_ids = Column(JSON, nullable=False)

    status = Column(
        Enum(BriefingJobStatus),
        nullable=False,
        default=BriefingJobStatus.queued
    )

    briefing_id = Column(Integer, ForeignKey("briefings.id"), nullable=True)
    error = Column(Text, nullable=True)

    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)
