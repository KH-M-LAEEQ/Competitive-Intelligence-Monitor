from datetime import datetime

from pydantic import BaseModel

from app.models.check_run import CheckRunStatus


class CheckRunResponse(BaseModel):
    id: int
    surface_id: int
    status: CheckRunStatus
    error: str | None = None
    started_at: datetime
    finished_at: datetime | None = None

    class Config:
        from_attributes = True
