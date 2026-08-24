from datetime import datetime

from sqlalchemy import Column, Integer, DateTime, JSON, ForeignKey
from app.base import Base


class CompetitorSiteSummary(Base):
    """LLM-extracted read of a competitor's *current* page content —
    product/service categories and live promotions — independent of the
    diff/materiality pipeline (see check_service.py). Deliberately a
    singleton per competitor (one row, overwritten on refresh) rather than
    a time series like TrafficSnapshot: this represents "what's on their
    site right now," not a history of it.
    """

    __tablename__ = "competitor_site_summaries"

    id = Column(Integer, primary_key=True, index=True)

    competitor_id = Column(
        Integer,
        ForeignKey("competitors.id"),
        nullable=False,
        unique=True
    )

    categories = Column(JSON, nullable=True)
    current_offers = Column(JSON, nullable=True)

    generated_at = Column(
        DateTime,
        default=datetime.utcnow
    )
