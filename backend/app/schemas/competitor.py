from datetime import datetime

from pydantic import BaseModel, HttpUrl


class CompetitorCreate(BaseModel):
    name: str
    website_url: HttpUrl | None = None


class CompetitorResponse(BaseModel):
    id: int
    name: str
    is_own_site: bool = False
    created_at: datetime | None = None
    surfaces_discovered: int = 0

    class Config:
        from_attributes = True