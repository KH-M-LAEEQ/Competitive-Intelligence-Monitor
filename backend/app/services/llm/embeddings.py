from sqlalchemy.orm import Session

from app.models.llm_usage import TokenUsageLog, LLMUsagePurpose
from app.services.budget_service import check_budget
from app.services.llm.client import LLMClient


def embed_and_log(
    db: Session, llm_client: LLMClient, workspace_id: int | None, texts: list[str]
) -> tuple[list[list[float]], str]:
    check_budget(db, workspace_id)

    result = llm_client.embed(texts)

    db.add(TokenUsageLog(
        workspace_id=workspace_id,
        purpose=LLMUsagePurpose.embedding,
        model=result.model,
        prompt_tokens=result.prompt_tokens,
        completion_tokens=0,
    ))

    return result.vectors, result.model
