from datetime import datetime

from pydantic import BaseModel, HttpUrl


class OwnSiteUpdate(BaseModel):
    url: HttpUrl


class OwnSiteResponse(BaseModel):
    competitor_id: int
    surface_id: int
    url: str
    check_frequency: str
    last_checked_at: datetime | None = None
