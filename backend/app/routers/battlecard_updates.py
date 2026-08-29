from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.battlecard_update import BattlecardUpdate
from app.models.workspace_member import WorkspaceMember
from app.schemas.battlecard import BattlecardUpdateResponse
from app.dependencies import get_current_workspace

# BattlecardUpdate rows carry workspace_id directly, so a single update can
# be looked up without knowing its competitor_id — used by the Approvals
# page to render a preview for battlecard_update items, which only have a
# workspace_id + item_id (the update's own id) to go on.
router = APIRouter(
    prefix="/workspaces/{workspace_id}/battlecard-updates",
    tags=["Battlecards"]
)


@router.get(
    "/{update_id}",
    response_model=BattlecardUpdateResponse
)
def get_battlecard_update(
    workspace_id: int,
    update_id: int,
    db: Session = Depends(get_db),
    membership: WorkspaceMember = Depends(get_current_workspace)
):

    update = (
        db.query(BattlecardUpdate)
        .filter(BattlecardUpdate.id == update_id, BattlecardUpdate.workspace_id == workspace_id)
        .first()
    )
    if update is None:
        raise HTTPException(status_code=404, detail="Battlecard update not found")

    return update
