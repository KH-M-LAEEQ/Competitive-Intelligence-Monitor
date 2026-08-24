from datetime import datetime

from sqlalchemy import Column, Integer, String, Date, DateTime, ForeignKey, UniqueConstraint
from app.base import Base


class TrafficSnapshot(Base):
    """One provider's estimated monthly visit count for a competitor's
    domain. Kept as a per-month time series (rather than a single "current"
    value on CompanyProfile) so a refresh accumulates a trend instead of
    overwriting the only data point — the whole point of tracking this is
    to see it move over time.
    """

    __tablename__ = "traffic_snapshots"
    __table_args__ = (
        UniqueConstraint("competitor_id", "month", "source", name="uq_traffic_snapshot_month"),
    )

    id = Column(Integer, primary_key=True, index=True)

    competitor_id = Column(Integer, ForeignKey("competitors.id"), nullable=False)
    domain = Column(String, nullable=False)

    month = Column(Date, nullable=False)
    visits = Column(Integer, nullable=True)

    source = Column(String, nullable=False, default="similarweb")
    fetched_at = Column(DateTime, default=datetime.utcnow)
