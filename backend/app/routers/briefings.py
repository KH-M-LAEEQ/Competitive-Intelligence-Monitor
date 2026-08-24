from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.briefing import Briefing
from app.models.user import User
from app.models.workspace_member import WorkspaceMember, WorkspaceRole
from app.schemas.briefing import GenerateBriefingRequest, BriefingResponse
from app.dependencies import get_current_user, get_current_workspace, require_role, rate_limit
from app.services.llm.factory import get_llm_client
from app.services.briefing_service import generate_briefing, NoMatchingChangeLogs
from app.services.budget_service import BudgetExceededError

router = APIRouter(
    prefix="/workspaces/{workspace_id}/briefings",
    tags=["Briefings"]
)


@router.post(
    "/generate-now",
    response_model=BriefingResponse
)
def generate_now(
    workspace_id: int,
    payload: GenerateBriefingRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    membership: WorkspaceMember = Depends(require_role(WorkspaceRole.owner, WorkspaceRole.editor)),
    _rate_limit: None = Depends(rate_limit("briefing-generate"))
):

    llm_client = get_llm_client()
    if llm_client is None:
        raise HTTPException(
            status_code=400,
            detail="No LLM is configured for this deployment"
        )

    try:
        briefing = generate_briefing(
            db, llm_client, workspace_id,
            payload.audience, payload.digest_type, payload.change_log_ids,
            generated_by_user_id=current_user.id
        )
    except NoMatchingChangeLogs as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except BudgetExceededError as exc:
        raise HTTPException(status_code=402, detail=str(exc))

    return briefing


@router.get(
    "/",
    response_model=list[BriefingResponse]
)
def list_briefings(
    workspace_id: int,
    db: Session = Depends(get_db),
    membership: WorkspaceMember = Depends(get_current_workspace)
):

    return (
        db.query(Briefing)
        .filter(Briefing.workspace_id == workspace_id)
        .order_by(Briefing.created_at.desc())
        .all()
    )


@router.get(
    "/{briefing_id}",
    response_model=BriefingResponse
)
def get_briefing(
    workspace_id: int,
    briefing_id: int,
    db: Session = Depends(get_db),
    membership: WorkspaceMember = Depends(get_current_workspace)
):

    briefing = (
        db.query(Briefing)
        .filter(Briefing.id == briefing_id, Briefing.workspace_id == workspace_id)
        .first()
    )

    if briefing is None:
        raise HTTPException(status_code=404, detail="Briefing not found")

    return briefing
