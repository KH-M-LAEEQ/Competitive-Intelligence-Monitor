from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.briefing import Briefing
from app.models.workspace_member import WorkspaceMember
from app.dependencies import get_current_workspace
from app.services.export_service import (
    export_change_logs_csv, export_change_logs_docx, export_briefing_pdf
)

router = APIRouter(
    prefix="/workspaces/{workspace_id}/exports",
    tags=["Exports"]
)


@router.get("/change-logs.csv")
def download_change_logs_csv(
    workspace_id: int,
    db: Session = Depends(get_db),
    membership: WorkspaceMember = Depends(get_current_workspace)
):

    content = export_change_logs_csv(db, workspace_id)

    return Response(
        content=content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=change-logs.csv"}
    )


@router.get("/change-logs.docx")
def download_change_logs_docx(
    workspace_id: int,
    db: Session = Depends(get_db),
    membership: WorkspaceMember = Depends(get_current_workspace)
):

    content = export_change_logs_docx(db, workspace_id)

    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": "attachment; filename=change-logs.docx"}
    )


@router.get("/briefings/{briefing_id}.pdf")
def download_briefing_pdf(
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

    content = export_briefing_pdf(briefing)

    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=briefing-{briefing_id}.pdf"}
    )
