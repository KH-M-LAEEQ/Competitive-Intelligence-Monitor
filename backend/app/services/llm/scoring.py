import logging
from typing import Literal

from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.models.llm_usage import TokenUsageLog, LLMUsagePurpose
from app.services.budget_service import check_budget
from app.services.llm.client import LLMClient
from app.services.llm.prompts import MATERIALITY_SYSTEM_PROMPT, materiality_user_prompt
from app.services.prompt_guard import scan_for_injection_markers

logger = logging.getLogger(__name__)


class ChangeItem(BaseModel):
    item: str
    before: str | None = None
    after: str
    change_type: Literal[
        "price_drop", "price_increase", "new", "removed", "policy", "other",
    ]
    change_pct: float | None = None


class MaterialityResult(BaseModel):
    score: int
    classification: Literal[
        "pricing_move", "new_feature", "positioning_shift",
        "hiring_signal", "promotion", "other",
    ]
    rationale: str
    highlights: list[str] = []
    headline: str | None = None
    items: list[ChangeItem] = []


def score_and_classify(
    db: Session,
    llm_client: LLMClient,
    workspace_id: int,
    surface_label: str,
    diff_text: str,
) -> MaterialityResult:
    markers = scan_for_injection_markers(diff_text)
    if markers:
        logger.warning(
            "Possible prompt-injection markers in scraped content (workspace %s): %s",
            workspace_id, markers,
        )

    check_budget(db, workspace_id)

    result = llm_client.complete(
        system=MATERIALITY_SYSTEM_PROMPT,
        user=materiality_user_prompt(surface_label, diff_text),
        response_model=MaterialityResult,
    )

    db.add(TokenUsageLog(
        workspace_id=workspace_id,
        purpose=LLMUsagePurpose.scoring,
        model=result.model,
        prompt_tokens=result.prompt_tokens,
        completion_tokens=result.completion_tokens,
    ))

    return result.value
