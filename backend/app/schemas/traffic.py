from datetime import date, datetime

from pydantic import BaseModel


class TrafficSnapshotResponse(BaseModel):
    id: int
    competitor_id: int
    domain: str
    month: date
    visits: int | None = None
    source: str
    fetched_at: datetime | None = None

    class Config:
        from_attributes = True
