from datetime import datetime

from pydantic import BaseModel

from app.models.briefing import BriefingAudience, BriefingDigestType, BriefingStatus
from app.models.briefing_job import BriefingJobStatus


class GenerateBriefingRequest(BaseModel):
    audience: BriefingAudience = BriefingAudience.all
    digest_type: BriefingDigestType = BriefingDigestType.urgent
    change_log_ids: list[int]


class BriefingResponse(BaseModel):
    id: int
    workspace_id: int
    audience: BriefingAudience
    digest_type: BriefingDigestType
    title: str
    body_markdown: str
    status: BriefingStatus
    created_at: datetime
    decided_at: datetime | None = None
    delivered_at: datetime | None = None

    class Config:
        from_attributes = True


class BriefingJobResponse(BaseModel):
    id: int
    status: BriefingJobStatus
    briefing_id: int | None = None
    error: str | None = None
    created_at: datetime
    finished_at: datetime | None = None

    class Config:
        from_attributes = True
