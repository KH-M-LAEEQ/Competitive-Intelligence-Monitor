from datetime import datetime

from pydantic import BaseModel


class AuditLogResponse(BaseModel):
    id: int
    actor_user_id: int | None = None
    action: str
    entity_type: str
    entity_id: int | None = None
    extra_data: dict | None = None
    created_at: datetime

    class Config:
        from_attributes = True
