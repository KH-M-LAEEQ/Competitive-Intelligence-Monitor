from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.competitor import Competitor
from app.models.competitor_site_summary import CompetitorSiteSummary
from app.models.workspace_member import WorkspaceMember, WorkspaceRole
from app.schemas.site_summary import SiteSummaryResponse
from app.dependencies import get_current_workspace, require_role, rate_limit
from app.services.budget_service import BudgetExceededError
from app.services.llm.factory import get_llm_client
from app.services.site_summary_service import generate_site_summary, NoSnapshotAvailable

router = APIRouter(
    prefix="/workspaces/{workspace_id}/competitors/{competitor_id}/site-summary",
    tags=["Site Summary"]
)


def _get_owned_competitor(db: Session, workspace_id: int, competitor_id: int) -> Competitor:
    competitor = (
        db.query(Competitor)
        .filter(Competitor.id == competitor_id, Competitor.workspace_id == workspace_id)
        .first()
    )
    if not competitor:
        raise HTTPException(status_code=404, detail="Competitor not found")
    return competitor


@router.get(
    "/",
    response_model=SiteSummaryResponse
)
def get_site_summary(
    workspace_id: int,
    competitor_id: int,
    db: Session = Depends(get_db),
    membership: WorkspaceMember = Depends(get_current_workspace)
):

    _get_owned_competitor(db, workspace_id, competitor_id)

    summary = (
        db.query(CompetitorSiteSummary)
        .filter(CompetitorSiteSummary.competitor_id == competitor_id)
        .first()
    )
    if summary is None:
        raise HTTPException(status_code=404, detail="No site summary generated yet")

    return summary


@router.post(
    "/refresh",
    response_model=SiteSummaryResponse
)
def refresh_site_summary(
    workspace_id: int,
    competitor_id: int,
    db: Session = Depends(get_db),
    membership: WorkspaceMember = Depends(require_role(WorkspaceRole.owner, WorkspaceRole.editor)),
    _rate_limit: None = Depends(rate_limit("site-summary-refresh", limit=10, window_seconds=3600.0))
):

    _get_owned_competitor(db, workspace_id, competitor_id)

    llm_client = get_llm_client()
    if llm_client is None:
        raise HTTPException(status_code=400, detail="No LLM is configured for this deployment")

    try:
        return generate_site_summary(db, llm_client, workspace_id, competitor_id)
    except NoSnapshotAvailable as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except BudgetExceededError as exc:
        raise HTTPException(status_code=402, detail=str(exc))
