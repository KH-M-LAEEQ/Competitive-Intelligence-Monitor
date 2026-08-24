from pydantic import BaseModel


class TrendsResponse(BaseModel):
    summary: str | None
    based_on: int


class SimilarChangeResponse(BaseModel):
    change_log_id: int
    competitor_id: int
    classification: str | None
    rationale: str | None
    similarity: float
