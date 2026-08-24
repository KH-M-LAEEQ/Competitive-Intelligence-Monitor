from datetime import datetime

from pydantic import BaseModel, EmailStr

from app.models.workspace_member import WorkspaceRole


class WorkspaceCreate(BaseModel):
    name: str


class WorkspaceResponse(BaseModel):
    id: int
    name: str
    slug: str
    created_at: datetime

    class Config:
        from_attributes = True


class WorkspaceWithRole(WorkspaceResponse):
    role: WorkspaceRole


class MemberInvite(BaseModel):
    email: EmailStr
    role: WorkspaceRole = WorkspaceRole.editor


class MemberRoleUpdate(BaseModel):
    role: WorkspaceRole


class MemberResponse(BaseModel):
    id: int
    user_id: int
    email: str
    full_name: str | None = None
    role: WorkspaceRole
    created_at: datetime

    class Config:
        from_attributes = True
