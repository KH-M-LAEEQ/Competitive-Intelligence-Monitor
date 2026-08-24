import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from apscheduler.jobstores.base import JobLookupError

from app.database import SessionLocal
from app.models.surface import Surface
from app.models.briefing import Briefing, BriefingStatus, BriefingDigestType
from app.services.check_service import run_surface_check
from app.services.snapshot_service import FetchError

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()

# In-process, single-instance scheduler (per project decision — no Redis/Celery).
# Running more than one app process/replica will double-fire these jobs; if this
# ever needs to scale horizontally, replace this module with a Redis-backed queue
# (Celery/RQ) rather than adding locking here.
_FREQUENCY_INTERVALS = {
    "hourly": {"hours": 1},
    "daily": {"hours": 24},
    "weekly": {"days": 7},
}


def _job_id(surface_id: int) -> str:
    return f"surface-check-{surface_id}"


def run_scheduled_check(surface_id: int) -> None:
    db = SessionLocal()
    try:
        surface = db.query(Surface).filter(Surface.id == surface_id).first()
        if surface is None or not surface.is_active:
            return

        try:
            result = run_surface_check(db, surface)
            logger.info("Scheduled check for surface %s: %s", surface_id, result.get("status"))
        except FetchError as exc:
            logger.warning("Scheduled check failed for surface %s: %s", surface_id, exc)
    finally:
        db.close()


def schedule_surface(surface: Surface) -> None:
    interval = _FREQUENCY_INTERVALS.get(surface.check_frequency, _FREQUENCY_INTERVALS["daily"])

    scheduler.add_job(
        run_scheduled_check,
        trigger=IntervalTrigger(**interval),
        args=[surface.id],
        id=_job_id(surface.id),
        replace_existing=True,
        misfire_grace_time=300,
        jitter=60,
    )


def unschedule_surface(surface_id: int) -> None:
    try:
        scheduler.remove_job(_job_id(surface_id))
    except JobLookupError:
        pass


def _run_digests_for_type(digest_type: BriefingDigestType) -> None:
    from app.services.delivery.delivery_service import deliver_digest

    db = SessionLocal()
    try:
        workspace_ids = [
            row[0] for row in
            db.query(Briefing.workspace_id)
            .filter(Briefing.status == BriefingStatus.approved, Briefing.digest_type == digest_type)
            .distinct()
            .all()
        ]
    finally:
        db.close()

    for workspace_id in workspace_ids:
        digest_db = SessionLocal()
        try:
            deliver_digest(digest_db, workspace_id, digest_type)
        except Exception as exc:  # noqa: BLE001 — one workspace's digest failing must not skip the rest
            logger.warning("Digest delivery failed for workspace %s: %s", workspace_id, exc)
        finally:
            digest_db.close()


def _run_daily_digests() -> None:
    _run_digests_for_type(BriefingDigestType.daily)


def _run_weekly_digests() -> None:
    _run_digests_for_type(BriefingDigestType.weekly)


def schedule_digest_jobs() -> None:
    """Two global cron jobs (not one per workspace) — cadence is a fixed
    daily/weekly schedule rather than a per-surface interval, so each job
    just queries across every workspace that has approved, undelivered
    briefings at that cadence when it fires.
    """
    scheduler.add_job(
        _run_daily_digests, CronTrigger(hour=8, minute=0),
        id="digest-daily", replace_existing=True,
    )
    scheduler.add_job(
        _run_weekly_digests, CronTrigger(day_of_week="mon", hour=8, minute=0),
        id="digest-weekly", replace_existing=True,
    )


def start_scheduler() -> None:
    db = SessionLocal()
    try:
        active_surfaces = db.query(Surface).filter(Surface.is_active.is_(True)).all()
        for surface in active_surfaces:
            schedule_surface(surface)
    finally:
        db.close()

    schedule_digest_jobs()
    scheduler.start()


def stop_scheduler() -> None:
    scheduler.shutdown(wait=False)
