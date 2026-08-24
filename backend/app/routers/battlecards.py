from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.competitor import Competitor
from app.models.battlecard import Battlecard
from app.models.battlecard_update import BattlecardUpdate
from app.models.user import User
from app.models.workspace_member import WorkspaceMember, WorkspaceRole
from app.schemas.battlecard import (
    ProposeBattlecardUpdateRequest, BattlecardResponse, BattlecardUpdateResponse
)
from app.dependencies import get_current_user, get_current_workspace, require_role, rate_limit
from app.services.llm.factory import get_llm_client
from app.services.battlecard_service import draft_update_from_change_logs, NoMatchingChangeLogs
from app.services.budget_service import BudgetExceededError

router = APIRouter(
    prefix="/workspaces/{workspace_id}/competitors/{competitor_id}/battlecard",
    tags=["Battlecards"]
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
    response_model=BattlecardResponse
)
def get_battlecard(
    workspace_id: int,
    competitor_id: int,
    db: Session = Depends(get_db),
    membership: WorkspaceMember = Depends(get_current_workspace)
):

    _get_owned_competitor(db, workspace_id, competitor_id)

    battlecard = (
        db.query(Battlecard)
        .filter(Battlecard.competitor_id == competitor_id, Battlecard.workspace_id == workspace_id)
        .first()
    )
    if battlecard is None:
        raise HTTPException(status_code=404, detail="No battlecard yet for this competitor")

    return battlecard


@router.post(
    "/updates",
    response_model=BattlecardUpdateResponse
)
def propose_update(
    workspace_id: int,
    competitor_id: int,
    payload: ProposeBattlecardUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    membership: WorkspaceMember = Depends(require_role(WorkspaceRole.owner, WorkspaceRole.editor)),
    _rate_limit: None = Depends(rate_limit("battlecard-propose"))
):

    _get_owned_competitor(db, workspace_id, competitor_id)

    llm_client = get_llm_client()
    if llm_client is None:
        raise HTTPException(status_code=400, detail="No LLM is configured for this deployment")

    try:
        update = draft_update_from_change_logs(
            db, llm_client, workspace_id, competitor_id,
            payload.change_log_ids, created_by_user_id=current_user.id
        )
    except NoMatchingChangeLogs as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except BudgetExceededError as exc:
        raise HTTPException(status_code=402, detail=str(exc))

    return update


@router.get(
    "/updates",
    response_model=list[BattlecardUpdateResponse]
)
def list_updates(
    workspace_id: int,
    competitor_id: int,
    db: Session = Depends(get_db),
    membership: WorkspaceMember = Depends(get_current_workspace)
):

    _get_owned_competitor(db, workspace_id, competitor_id)

    battlecard = (
        db.query(Battlecard)
        .filter(Battlecard.competitor_id == competitor_id, Battlecard.workspace_id == workspace_id)
        .first()
    )
    if battlecard is None:
        return []

    return (
        db.query(BattlecardUpdate)
        .filter(BattlecardUpdate.battlecard_id == battlecard.id)
        .order_by(BattlecardUpdate.created_at.desc())
        .all()
    )
