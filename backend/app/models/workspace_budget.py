from datetime import datetime

from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey
from app.base import Base


class WorkspaceBudget(Base):
    """Per-workspace LLM spend cap. Populated now (Phase 3) alongside usage
    logging so nothing needs retrofitting later, but not yet enforced —
    enforcement (rejecting calls once a workspace exceeds its cap) is
    Phase 12's job.
    """

    __tablename__ = "workspace_budgets"

    workspace_id = Column(
        Integer,
        ForeignKey("workspaces.id"),
        primary_key=True
    )

    monthly_cap_usd = Column(Float, nullable=True)
    period_start = Column(DateTime, default=datetime.utcnow)
    alert_threshold_pct = Column(Float, nullable=True, default=80.0)
