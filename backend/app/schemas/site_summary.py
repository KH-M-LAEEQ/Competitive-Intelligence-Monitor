from datetime import datetime

from pydantic import BaseModel


class SiteSummaryResponse(BaseModel):
    competitor_id: int
    categories: list[str]
    current_offers: list[str]
    generated_at: datetime | None = None

    class Config:
        from_attributes = True
