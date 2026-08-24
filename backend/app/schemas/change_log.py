from pydantic import BaseModel
from datetime import datetime


class ChangeLogResponse(BaseModel):
    id: int
    competitor_id: int
    surface_id: int
    diff: str | None = None
    materiality_score: int | None = None
    classification: str | None = None
    rationale: str | None = None
    highlights: list[str] | None = None
    headline: str | None = None
    items: list[dict] | None = None
    visual_diff_score: float | None = None
    created_at: datetime

    class Config:
        from_attributes = True