import enum
from datetime import datetime

from sqlalchemy import Column, Integer, Text, DateTime, Enum, ForeignKey
from app.base import Base


class CheckRunStatus(str, enum.Enum):
    running = "running"
    success = "success"
    failed = "failed"


class CheckRun(Base):
    __tablename__ = "check_runs"

    id = Column(Integer, primary_key=True, index=True)

    surface_id = Column(
        Integer,
        ForeignKey("surfaces.id"),
        nullable=False
    )

    status = Column(
        Enum(CheckRunStatus),
        nullable=False,
        default=CheckRunStatus.running
    )

    error = Column(Text, nullable=True)

    started_at = Column(
        DateTime,
        default=datetime.utcnow
    )

    finished_at = Column(DateTime, nullable=True)
