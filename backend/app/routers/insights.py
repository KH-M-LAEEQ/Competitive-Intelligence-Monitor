from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.change_log import ChangeLog
from app.models.competitor import Competitor
from app.models.workspace_member import WorkspaceMember
from app.schemas.insight import TrendsResponse, SimilarChangeResponse
from app.dependencies import get_current_workspace, rate_limit
from app.services.llm.factory import get_llm_client
from app.services.synthesis import generate_cross_competitor_summary, find_similar_changes
from app.services.budget_service import BudgetExceededError

router = APIRouter(
    prefix="/workspaces/{workspace_id}/insights",
    tags=["Insights"]
)


@router.get(
    "/trends",
    response_model=TrendsResponse
)
def get_trends(
    workspace_id: int,
    days: int = 14,
    db: Session = Depends(get_db),
    membership: WorkspaceMember = Depends(get_current_workspace),
    _rate_limit: None = Depends(rate_limit("insights-trends"))
):

    llm_client = get_llm_client()
    if llm_client is None:
        return TrendsResponse(summary=None, based_on=0)

    since = datetime.utcnow() - timedelta(days=days)
    try:
        outcome = generate_cross_competitor_summary(db, llm_client, workspace_id, since)
    except BudgetExceededError:
        # A dashboard "insight" endpoint degrading to no-summary is a much
        # better UX than a GET request erroring out — unlike an explicit
        # user action (generate a briefing), nobody is blocked by this.
        return TrendsResponse(summary=None, based_on=0)
    db.commit()

    if outcome is None:
        return TrendsResponse(summary=None, based_on=0)

    return TrendsResponse(summary=outcome.summary, based_on=outcome.based_on)


@router.get(
    "/change-logs/{change_log_id}/similar",
    response_model=list[SimilarChangeResponse]
)
def get_similar_changes(
    workspace_id: int,
    change_log_id: int,
    top_k: int = 5,
    db: Session = Depends(get_db),
    membership: WorkspaceMember = Depends(get_current_workspace)
):

    change_log = (
        db.query(ChangeLog)
        .join(Competitor, ChangeLog.competitor_id == Competitor.id)
        .filter(ChangeLog.id == change_log_id, Competitor.workspace_id == workspace_id)
        .first()
    )
    if change_log is None:
        raise HTTPException(status_code=404, detail="Change log not found")

    similar = find_similar_changes(db, workspace_id, change_log_id, top_k=top_k)

    return [
        SimilarChangeResponse(
            change_log_id=s.change_log.id,
            competitor_id=s.change_log.competitor_id,
            classification=s.change_log.classification,
            rationale=s.change_log.rationale,
            similarity=s.similarity,
        )
        for s in similar
    ]
