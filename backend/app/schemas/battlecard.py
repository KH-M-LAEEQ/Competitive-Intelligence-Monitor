from datetime import datetime

from pydantic import BaseModel

from app.models.approval_item import ApprovalStatus


class ProposeBattlecardUpdateRequest(BaseModel):
    change_log_ids: list[int]


class BattlecardResponse(BaseModel):
    id: int
    workspace_id: int
    competitor_id: int
    title: str
    content_markdown: str
    version: int
    updated_at: datetime | None = None

    class Config:
        from_attributes = True


class BattlecardUpdateResponse(BaseModel):
    id: int
    battlecard_id: int
    proposed_content_markdown: str
    change_summary: str | None = None
    status: ApprovalStatus
    created_at: datetime
    decided_at: datetime | None = None

    class Config:
        from_attributes = True
