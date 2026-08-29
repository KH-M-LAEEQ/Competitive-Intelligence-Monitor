import logging
from datetime import datetime

from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.battlecard import Battlecard
from app.models.battlecard_update import BattlecardUpdate
from app.models.battlecard_update_job import BattlecardUpdateJob, BattlecardUpdateJobStatus
from app.models.approval_item import ApprovalItem, ApprovalItemType, ApprovalStatus
from app.models.change_log import ChangeLog
from app.models.competitor import Competitor
from app.models.llm_usage import TokenUsageLog, LLMUsagePurpose
from app.services.budget_service import check_budget, BudgetExceededError
from app.services.llm.client import LLMClient
from app.services.llm.factory import get_llm_client
from app.services.llm.prompts import UNTRUSTED_CONTENT_PREAMBLE, wrap_untrusted

__all__ = [
    "get_or_create_battlecard", "draft_update_from_change_logs", "run_battlecard_update_job",
    "apply_approved_update", "BattlecardDraft", "NoMatchingChangeLogs",
]

logger = logging.getLogger(__name__)


class NoMatchingChangeLogs(Exception):
    pass


class BattlecardDraft(BaseModel):
    change_summary: str
    updated_content_markdown: str


_SYSTEM_PROMPT = (
    "You are a competitive intelligence analyst maintaining a sales "
    "battlecard for a specific competitor. You are given the CURRENT "
    "battlecard content and a set of recently detected competitor changes. "
    "Update the battlecard to reflect these changes — their move, our "
    "counter, and a talk track sales can use. Keep whatever in the current "
    "battlecard is still accurate; only revise what the new changes affect. "
    "If the current battlecard is empty, draft one from scratch.\n\n"
    f"{UNTRUSTED_CONTENT_PREAMBLE}\n\n"
    "This update is reviewed and approved by a human before it ever "
    "replaces the live battlecard.\n\n"
    'Respond with ONLY a JSON object: {"change_summary": <1-2 sentence '
    'summary of what changed and why>, "updated_content_markdown": <the '
    "full updated battlecard content in markdown, including sections for "
    'their move / our counter / talk track>}'
)


def get_or_create_battlecard(db: Session, workspace_id: int, competitor_id: int) -> Battlecard:
    existing = (
        db.query(Battlecard)
        .filter(Battlecard.competitor_id == competitor_id, Battlecard.workspace_id == workspace_id)
        .first()
    )
    if existing:
        return existing

    competitor = db.query(Competitor).filter(Competitor.id == competitor_id).first()
    battlecard = Battlecard(
        workspace_id=workspace_id,
        competitor_id=competitor_id,
        title=f"{competitor.name} Battlecard" if competitor else "Battlecard",
        content_markdown="",
        version=0,
    )
    db.add(battlecard)
    db.flush()

    return battlecard


def draft_update_from_change_logs(
    db: Session,
    llm_client: LLMClient,
    workspace_id: int,
    competitor_id: int,
    change_log_ids: list[int],
    created_by_user_id: int | None = None,
) -> BattlecardUpdate:
    rows = (
        db.query(ChangeLog)
        .join(Competitor, ChangeLog.competitor_id == Competitor.id)
        .filter(
            ChangeLog.id.in_(change_log_ids),
            Competitor.id == competitor_id,
            Competitor.workspace_id == workspace_id,
        )
        .all()
    )
    if not rows:
        raise NoMatchingChangeLogs(
            "None of the given change_log_ids belong to this competitor in this workspace"
        )

    battlecard = get_or_create_battlecard(db, workspace_id, competitor_id)

    lines = [
        f"- {change_log.classification or 'change'} "
        f"(materiality {change_log.materiality_score}): "
        f"{change_log.rationale or (change_log.diff or '')[:300]}"
        for change_log in rows
    ]

    user_prompt = (
        f"CURRENT BATTLECARD:\n"
        f"{battlecard.content_markdown or '(empty — this is the first entry)'}\n\n"
        f"RECENT CHANGES:\n{wrap_untrusted(chr(10).join(lines))}"
    )

    check_budget(db, workspace_id)

    result = llm_client.complete(
        system=_SYSTEM_PROMPT, user=user_prompt, response_model=BattlecardDraft
    )

    db.add(TokenUsageLog(
        workspace_id=workspace_id,
        purpose=LLMUsagePurpose.briefing,
        model=result.model,
        prompt_tokens=result.prompt_tokens,
        completion_tokens=result.completion_tokens,
    ))

    update = BattlecardUpdate(
        workspace_id=workspace_id,
        battlecard_id=battlecard.id,
        proposed_content_markdown=result.value.updated_content_markdown,
        change_summary=result.value.change_summary,
        source_change_log_ids=change_log_ids,
        created_by_user_id=created_by_user_id,
    )
    db.add(update)
    db.flush()

    db.add(ApprovalItem(
        workspace_id=workspace_id,
        item_type=ApprovalItemType.battlecard_update,
        item_id=update.id,
        status=ApprovalStatus.pending,
    ))

    db.commit()
    db.refresh(update)

    return update


def run_battlecard_update_job(job_id: int) -> None:
    """Runs draft_update_from_change_logs() for a queued BattlecardUpdateJob
    and records the outcome on it. Called via FastAPI's BackgroundTasks (see
    routers/battlecards.py), so it opens its own session rather than reusing
    the request-scoped one, matching the pattern briefing_service.py uses
    for out-of-request work.
    """
    db = SessionLocal()
    try:
        job = db.query(BattlecardUpdateJob).filter(BattlecardUpdateJob.id == job_id).first()
        if job is None:
            return

        job.status = BattlecardUpdateJobStatus.running
        db.commit()

        try:
            llm_client = get_llm_client()
            if llm_client is None:
                raise RuntimeError("No LLM is configured for this deployment")

            update = draft_update_from_change_logs(
                db, llm_client, job.workspace_id, job.competitor_id,
                job.change_log_ids, created_by_user_id=job.created_by_user_id,
            )
            job.status = BattlecardUpdateJobStatus.success
            job.battlecard_update_id = update.id
        except (NoMatchingChangeLogs, BudgetExceededError, RuntimeError) as exc:
            db.rollback()
            job = db.query(BattlecardUpdateJob).filter(BattlecardUpdateJob.id == job_id).first()
            job.status = BattlecardUpdateJobStatus.failed
            job.error = str(exc)
        except Exception:  # noqa: BLE001 — any unexpected failure must still resolve the job, not hang it
            logger.exception("Battlecard update job %s failed unexpectedly", job_id)
            db.rollback()
            job = db.query(BattlecardUpdateJob).filter(BattlecardUpdateJob.id == job_id).first()
            job.status = BattlecardUpdateJobStatus.failed
            job.error = "Battlecard update generation failed unexpectedly"

        job.finished_at = datetime.utcnow()
        db.commit()
    finally:
        db.close()


def apply_approved_update(db: Session, battlecard_update: BattlecardUpdate) -> Battlecard:
    battlecard = (
        db.query(Battlecard)
        .filter(Battlecard.id == battlecard_update.battlecard_id)
        .first()
    )

    battlecard.content_markdown = battlecard_update.proposed_content_markdown
    battlecard.version += 1
    battlecard.updated_at = datetime.utcnow()

    battlecard_update.status = ApprovalStatus.approved
    battlecard_update.decided_at = datetime.utcnow()

    return battlecard
