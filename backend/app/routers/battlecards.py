from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.competitor import Competitor
from app.models.battlecard import Battlecard
from app.models.battlecard_update import BattlecardUpdate
from app.models.battlecard_update_job import BattlecardUpdateJob, BattlecardUpdateJobStatus
from app.models.user import User
from app.models.workspace_member import WorkspaceMember, WorkspaceRole
from app.schemas.battlecard import (
    ProposeBattlecardUpdateRequest, BattlecardResponse, BattlecardUpdateResponse,
    BattlecardUpdateJobResponse,
)
from app.dependencies import get_current_user, get_current_workspace, require_role, rate_limit
from app.services.llm.factory import get_llm_client
from app.services.battlecard_service import run_battlecard_update_job

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
    response_model=BattlecardUpdateJobResponse,
    status_code=202
)
def propose_update(
    workspace_id: int,
    competitor_id: int,
    payload: ProposeBattlecardUpdateRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    membership: WorkspaceMember = Depends(require_role(WorkspaceRole.owner, WorkspaceRole.editor)),
    _rate_limit: None = Depends(rate_limit("battlecard-propose"))
):

    _get_owned_competitor(db, workspace_id, competitor_id)

    llm_client = get_llm_client()
    if llm_client is None:
        raise HTTPException(status_code=400, detail="No LLM is configured for this deployment")

    job = BattlecardUpdateJob(
        workspace_id=workspace_id,
        competitor_id=competitor_id,
        change_log_ids=payload.change_log_ids,
        status=BattlecardUpdateJobStatus.queued,
        created_by_user_id=current_user.id,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    background_tasks.add_task(run_battlecard_update_job, job.id)

    return job


@router.get(
    "/updates/jobs/{job_id}",
    response_model=BattlecardUpdateJobResponse
)
def get_battlecard_update_job(
    workspace_id: int,
    competitor_id: int,
    job_id: int,
    db: Session = Depends(get_db),
    membership: WorkspaceMember = Depends(get_current_workspace)
):

    job = (
        db.query(BattlecardUpdateJob)
        .filter(
            BattlecardUpdateJob.id == job_id,
            BattlecardUpdateJob.workspace_id == workspace_id,
            BattlecardUpdateJob.competitor_id == competitor_id,
        )
        .first()
    )

    if job is None:
        raise HTTPException(status_code=404, detail="Battlecard update job not found")

    return job


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
