from datetime import datetime

from pydantic import BaseModel

from app.models.workspace_integration import IntegrationProvider


class WorkspaceIntegrationUpsert(BaseModel):
    provider: IntegrationProvider
    config: dict
    enabled: bool = True


class WorkspaceIntegrationResponse(BaseModel):
    id: int
    workspace_id: int
    provider: IntegrationProvider
    config: dict
    enabled: bool
    created_at: datetime
    updated_at: datetime | None = None

    class Config:
        from_attributes = True


class TestSendResponse(BaseModel):
    success: bool
    detail: str | None = None
