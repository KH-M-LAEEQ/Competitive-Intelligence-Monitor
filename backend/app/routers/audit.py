from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.audit_log import AuditLog
from app.models.workspace_member import WorkspaceMember
from app.schemas.audit_log import AuditLogResponse
from app.dependencies import get_current_workspace

router = APIRouter(
    prefix="/workspaces/{workspace_id}/audit-log",
    tags=["Audit"]
)


@router.get(
    "/",
    response_model=list[AuditLogResponse]
)
def list_audit_log(
    workspace_id: int,
    limit: int = 100,
    db: Session = Depends(get_db),
    membership: WorkspaceMember = Depends(get_current_workspace)
):

    return (
        db.query(AuditLog)
        .filter(AuditLog.workspace_id == workspace_id)
        .order_by(AuditLog.created_at.desc())
        .limit(limit)
        .all()
    )
