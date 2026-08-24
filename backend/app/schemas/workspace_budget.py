from datetime import datetime

from pydantic import BaseModel


class WorkspaceBudgetResponse(BaseModel):
    workspace_id: int
    monthly_cap_usd: float | None
    period_start: datetime
    alert_threshold_pct: float | None
    estimated_spend_usd: float
    spend_by_purpose: dict[str, float]

    class Config:
        from_attributes = True


class WorkspaceBudgetUpdate(BaseModel):
    monthly_cap_usd: float | None = None
    alert_threshold_pct: float | None = None
