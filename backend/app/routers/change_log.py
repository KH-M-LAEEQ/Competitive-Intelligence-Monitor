from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.change_log import ChangeLog
from app.models.competitor import Competitor
from app.models.workspace_member import WorkspaceMember
from app.schemas.change_log import ChangeLogResponse
from app.dependencies import get_current_workspace

router = APIRouter(
    prefix="/workspaces/{workspace_id}/change-logs",
    tags=["Change Logs"]
)


@router.get(
    "/",
    response_model=list[ChangeLogResponse]
)
def get_change_logs(
    workspace_id: int,
    db: Session = Depends(get_db),
    membership: WorkspaceMember = Depends(get_current_workspace)
):
    return (
        db.query(ChangeLog)
        .join(Competitor, ChangeLog.competitor_id == Competitor.id)
        .filter(Competitor.workspace_id == workspace_id)
        .all()
    )