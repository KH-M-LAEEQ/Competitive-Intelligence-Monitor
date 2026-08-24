import logging
from datetime import datetime

from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.models.competitor_site_summary import CompetitorSiteSummary
from app.models.llm_usage import TokenUsageLog, LLMUsagePurpose
from app.models.snapshot import Snapshot
from app.models.surface import Surface
from app.services.budget_service import check_budget
from app.services.llm.client import LLMClient
from app.services.llm.prompts import SITE_SUMMARY_SYSTEM_PROMPT, site_summary_user_prompt
from app.services.rendered_content_service import capture_rendered_text, RenderedContentError

__all__ = ["generate_site_summary", "SiteSummaryDraft", "NoSnapshotAvailable"]

logger = logging.getLogger(__name__)


class NoSnapshotAvailable(Exception):
    pass


class SiteSummaryDraft(BaseModel):
    categories: list[str]
    current_offers: list[str]


def _latest_pages(db: Session, competitor_id: int) -> list[tuple[str, str]]:
    """One (label, text) pair per active surface. Always prefers a fresh
    JavaScript-rendered fetch (see rendered_content_service.py) over the
    stored Snapshot.text_content, since the stored snapshot comes from a
    plain HTTP fetch that misses anything a storefront renders client-side
    (hero banners, sale badges, category nav) — exactly the kind of content
    this feature needs, and the entire reason it exists (see the Bareeze
    bug this was built to fix: its real offers only ever showed up in the
    rendered fetch, never the plain-HTTP snapshot). Falls back to the
    stored snapshot only if rendering itself fails, so a flaky render never
    makes the whole thing unavailable — but a *successful but JS-empty*
    plain snapshot is never substituted for a working render, since that's
    what silently regressed this feature to "no categories found" before.

    This runs both from the manual "Analyze site" refresh and automatically
    after every check that finds new content (see
    check_service._apply_site_summary) — an extra browser launch once or
    twice a day per surface is not a real cost concern, and accuracy here
    matters more than shaving that cost.
    """

    surfaces = (
        db.query(Surface)
        .filter(Surface.competitor_id == competitor_id, Surface.is_active.is_(True))
        .all()
    )

    pages = []
    for surface in surfaces:
        label = f"{surface.surface_type.value} — {surface.url}"

        try:
            rendered_text = capture_rendered_text(surface.url)
            if rendered_text:
                pages.append((label, rendered_text))
                continue
        except RenderedContentError as exc:
            logger.warning("Rendered fetch failed for surface %s, falling back to last snapshot: %s", surface.id, exc)

        snapshot = (
            db.query(Snapshot)
            .filter(Snapshot.surface_id == surface.id)
            .order_by(Snapshot.id.desc())
            .first()
        )
        if snapshot is not None and snapshot.text_content:
            pages.append((label, snapshot.text_content))

    return pages


def generate_site_summary(
    db: Session, llm_client: LLMClient, workspace_id: int, competitor_id: int
) -> CompetitorSiteSummary:
    """Analyzes a competitor's *current* snapshot content — independent of
    the diff/materiality pipeline, so it's available even when zero changes
    have been detected yet. Upserts a singleton row per competitor (see
    CompetitorSiteSummary docstring) rather than accumulating a history.
    """

    pages = _latest_pages(db, competitor_id)
    if not pages:
        raise NoSnapshotAvailable(
            "This competitor has no captured snapshot yet — run a check first"
        )

    check_budget(db, workspace_id)

    result = llm_client.complete(
        system=SITE_SUMMARY_SYSTEM_PROMPT,
        user=site_summary_user_prompt(pages),
        response_model=SiteSummaryDraft,
    )

    db.add(TokenUsageLog(
        workspace_id=workspace_id,
        purpose=LLMUsagePurpose.site_summary,
        model=result.model,
        prompt_tokens=result.prompt_tokens,
        completion_tokens=result.completion_tokens,
    ))

    existing = (
        db.query(CompetitorSiteSummary)
        .filter(CompetitorSiteSummary.competitor_id == competitor_id)
        .first()
    )

    if existing:
        existing.categories = result.value.categories
        existing.current_offers = result.value.current_offers
        existing.generated_at = datetime.utcnow()
        summary = existing
    else:
        summary = CompetitorSiteSummary(
            competitor_id=competitor_id,
            categories=result.value.categories,
            current_offers=result.value.current_offers,
        )
        db.add(summary)

    db.commit()
    db.refresh(summary)
    return summary
