from datetime import datetime, timedelta

from app.scheduler import scheduler, schedule_surface, _job_id


class _FakeSurface:
    def __init__(self, id, check_frequency, last_checked_at):
        self.id = id
        self.check_frequency = check_frequency
        self.last_checked_at = last_checked_at


def test_overdue_surface_is_scheduled_to_run_immediately():
    # Backend restarts (every --reload in dev, every deploy) re-add every
    # job from scratch. A surface last checked 30h ago on a daily cadence is
    # already overdue — it must run on the next tick, not wait out another
    # full 24h from the restart.
    surface = _FakeSurface(
        id=101, check_frequency="daily",
        last_checked_at=datetime.utcnow() - timedelta(hours=30),
    )
    schedule_surface(surface)
    job = scheduler.get_job(_job_id(surface.id))
    assert job.next_run_time.replace(tzinfo=None) <= datetime.utcnow() + timedelta(seconds=1)


def test_not_yet_due_surface_keeps_its_remaining_wait():
    # Checked 2h ago on a daily cadence — next run should land ~22h out,
    # not reset to a fresh 24h from whenever the process happened to restart.
    surface = _FakeSurface(
        id=102, check_frequency="daily",
        last_checked_at=datetime.utcnow() - timedelta(hours=2),
    )
    schedule_surface(surface)
    job = scheduler.get_job(_job_id(surface.id))
    remaining = job.next_run_time.replace(tzinfo=None) - datetime.utcnow()
    assert timedelta(hours=21) < remaining < timedelta(hours=23)


def test_never_checked_surface_schedules_without_error():
    # No prior check at all — falls back to APScheduler's normal default
    # (now + interval) by omitting next_run_time entirely, same as before
    # this fix. (The scheduler isn't running in this test, so the job stays
    # pending and its resolved next_run_time isn't observable here — this
    # just guards against passing an explicit None, which APScheduler
    # treats as "add this job paused.")
    surface = _FakeSurface(id=103, check_frequency="daily", last_checked_at=None)
    schedule_surface(surface)
    assert scheduler.get_job(_job_id(surface.id)) is not None
