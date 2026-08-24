from datetime import datetime

from pydantic import BaseModel


class SnapshotResponse(BaseModel):
    id: int
    surface_id: int
    text_content: str | None
    summary: str | None = None
    highlights: list[str] | None = None
    headline: str | None = None
    facts: list[dict] | None = None
    created_at: datetime | None = None

    class Config:
        from_attributes = True
