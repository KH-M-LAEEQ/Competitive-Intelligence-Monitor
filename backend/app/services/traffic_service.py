import logging
from datetime import date, datetime

import requests
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.traffic_snapshot import TrafficSnapshot

logger = logging.getLogger(__name__)

__all__ = ["TrafficProviderError", "similarweb_configured", "fetch_and_store_traffic"]


class TrafficProviderError(Exception):
    pass


def similarweb_configured() -> bool:
    return bool(settings.similarweb_api_key)


def _month_start(d: date) -> date:
    return d.replace(day=1)


def _add_months(d: date, delta: int) -> date:
    month_index = d.month - 1 + delta
    year = d.year + month_index // 12
    month = month_index % 12 + 1
    return date(year, month, 1)


def fetch_and_store_traffic(
    db: Session, competitor_id: int, domain: str, months: int = 6
) -> list[TrafficSnapshot]:
    """Fetches the last `months` of monthly visit estimates from SimilarWeb
    and upserts one TrafficSnapshot row per (competitor, month) — a refresh
    updates existing months rather than duplicating them. Raises
    TrafficProviderError on any failure; this is only ever called from an
    explicit user-triggered refresh, so the caller surfaces the error
    directly rather than swallowing it.
    """

    if not settings.similarweb_api_key:
        raise TrafficProviderError("SimilarWeb is not configured for this deployment")

    today = _month_start(datetime.utcnow().date())
    end_date = _add_months(today, -1)  # last fully-completed month
    start_date = _add_months(end_date, -(months - 1))

    url = f"{settings.similarweb_base_url}/website/{domain}/total-traffic-and-engagement/visits"
    params = {
        "api_key": settings.similarweb_api_key,
        "start_date": start_date.strftime("%Y-%m"),
        "end_date": end_date.strftime("%Y-%m"),
        "country": "world",
        "granularity": "monthly",
        "main_domain_only": "false",
        "format": "json",
    }

    try:
        response = requests.get(url, params=params, timeout=20)
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException as exc:
        raise TrafficProviderError(f"SimilarWeb request failed: {exc}") from exc
    except ValueError as exc:
        raise TrafficProviderError(f"SimilarWeb returned a non-JSON response: {exc}") from exc

    entries = payload.get("visits")
    if entries is None:
        raise TrafficProviderError(f"Unexpected SimilarWeb response shape: {payload}")

    snapshots = []
    for entry in entries:
        try:
            month = datetime.strptime(entry["date"][:7], "%Y-%m").date().replace(day=1)
            visits = int(round(entry["visits"])) if entry.get("visits") is not None else None
        except (KeyError, ValueError) as exc:
            logger.warning("Skipping unparseable SimilarWeb entry %s: %s", entry, exc)
            continue

        existing = (
            db.query(TrafficSnapshot)
            .filter(
                TrafficSnapshot.competitor_id == competitor_id,
                TrafficSnapshot.month == month,
                TrafficSnapshot.source == "similarweb",
            )
            .first()
        )
        if existing:
            existing.visits = visits
            existing.domain = domain
            existing.fetched_at = datetime.utcnow()
            snapshots.append(existing)
        else:
            snapshot = TrafficSnapshot(
                competitor_id=competitor_id, domain=domain, month=month,
                visits=visits, source="similarweb",
            )
            db.add(snapshot)
            snapshots.append(snapshot)

    db.commit()
    for snapshot in snapshots:
        db.refresh(snapshot)

    return sorted(snapshots, key=lambda s: s.month)
