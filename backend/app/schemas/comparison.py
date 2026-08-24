from datetime import datetime

from pydantic import BaseModel

from app.schemas.competitor import CompetitorResponse
from app.schemas.company_profile import CompanyProfileResponse
from app.schemas.battlecard import BattlecardResponse
from app.schemas.traffic import TrafficSnapshotResponse


class CompetitorSummaryResponse(BaseModel):
    total_changes: int
    material_count: int
    avg_materiality: float | None = None
    classification_counts: dict[str, int]
    trend: list[dict]
    last_change_at: datetime | None = None

    class Config:
        from_attributes = True


class BenchmarkComparisonResponse(BaseModel):
    competitor: CompetitorResponse
    change_summary: CompetitorSummaryResponse
    traffic: list[TrafficSnapshotResponse] | None = None


class ComparisonResponse(BaseModel):
    competitor: CompetitorResponse
    profile: CompanyProfileResponse | None = None
    battlecard: BattlecardResponse | None = None
    change_summary: CompetitorSummaryResponse
    traffic: list[TrafficSnapshotResponse] | None = None
    # The "vs." benchmark — your own site if one is configured, otherwise
    # whichever other competitor was picked via ?compare_to= (competitor vs
    # competitor comparison when there's no own-site to measure against).
    benchmark: BenchmarkComparisonResponse | None = None
