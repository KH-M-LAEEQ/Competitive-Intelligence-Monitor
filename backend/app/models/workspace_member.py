import enum
from datetime import datetime

from sqlalchemy import Column, Integer, ForeignKey, DateTime, Enum, UniqueConstraint
from app.base import Base


class WorkspaceRole(str, enum.Enum):
    owner = "owner"
    editor = "editor"
    reviewer = "reviewer"


class WorkspaceMember(Base):
    __tablename__ = "workspace_members"
    __table_args__ = (
        UniqueConstraint("workspace_id", "user_id", name="uq_workspace_member"),
    )

    id = Column(Integer, primary_key=True, index=True)

    workspace_id = Column(
        Integer,
        ForeignKey("workspaces.id"),
        nullable=False
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False
    )

    role = Column(
        Enum(WorkspaceRole),
        nullable=False,
        default=WorkspaceRole.editor
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )
