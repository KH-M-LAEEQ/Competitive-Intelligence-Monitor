from datetime import datetime

from pydantic import BaseModel

from app.models.approval_item import ApprovalItemType, ApprovalStatus


class DecisionRequest(BaseModel):
    notes: str | None = None


class ApprovalItemResponse(BaseModel):
    id: int
    workspace_id: int
    item_type: ApprovalItemType
    item_id: int
    status: ApprovalStatus
    requested_at: datetime
    decided_by: int | None = None
    decided_at: datetime | None = None
    decision_notes: str | None = None

    class Config:
        from_attributes = True
