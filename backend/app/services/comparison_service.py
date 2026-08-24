from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models.change_log import ChangeLog

__all__ = ["CompetitorSummary", "summarize_competitor"]


@dataclass
class CompetitorSummary:
    total_changes: int
    material_count: int
    avg_materiality: float | None
    classification_counts: dict[str, int]
    trend: list[dict]
    last_change_at: datetime | None


def _day_key(dt: datetime) -> str:
    return dt.date().isoformat()


def summarize_competitor(db: Session, competitor_id: int, days: int = 30) -> CompetitorSummary:
    """Aggregates a single competitor's change history — the data behind
    both the Compare page's trend/classification charts and the Dashboard
    comparison table's per-row stats. Scoped to the last `days` days for the
    trend series, but totals/last_change_at look across all-time history so
    a competitor with no recent activity still shows its real numbers.
    """

    since = datetime.utcnow() - timedelta(days=days)

    all_logs = (
        db.query(ChangeLog)
        .filter(ChangeLog.competitor_id == competitor_id)
        .order_by(ChangeLog.created_at.asc())
        .all()
    )

    scored = [log for log in all_logs if log.materiality_score is not None]
    material = [log for log in scored if log.materiality_score >= 50]

    classification_counts: dict[str, int] = {}
    for log in all_logs:
        if log.classification:
            classification_counts[log.classification] = (
                classification_counts.get(log.classification, 0) + 1
            )

    buckets: dict[str, dict[str, int]] = {}
    today = datetime.utcnow()
    for i in range(days - 1, -1, -1):
        key = _day_key(today - timedelta(days=i))
        buckets[key] = {"detected": 0, "material": 0}

    for log in all_logs:
        if log.created_at is None or log.created_at < since:
            continue
        key = _day_key(log.created_at)
        if key not in buckets:
            continue
        buckets[key]["detected"] += 1
        if log.materiality_score is not None and log.materiality_score >= 50:
            buckets[key]["material"] += 1

    trend = [{"date": date, **counts} for date, counts in buckets.items()]

    avg_materiality = (
        sum(log.materiality_score for log in scored) / len(scored) if scored else None
    )

    return CompetitorSummary(
        total_changes=len(all_logs),
        material_count=len(material),
        avg_materiality=avg_materiality,
        classification_counts=classification_counts,
        trend=trend,
        last_change_at=all_logs[-1].created_at if all_logs else None,
    )
