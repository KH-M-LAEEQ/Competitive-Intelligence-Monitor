from sqlalchemy.orm import Session

from app.models.briefing import briefing_change_logs
from app.models.change_embedding import ChangeEmbedding
from app.models.change_log import ChangeLog
from app.models.check_run import CheckRun
from app.models.competitor import Competitor
from app.models.snapshot import Snapshot
from app.models.surface import Surface
from app.scheduler import schedule_surface, unschedule_surface

__all__ = ["get_own_site", "get_own_site_surface", "set_own_site", "delete_own_site"]


def get_own_site(db: Session, workspace_id: int) -> Competitor | None:
    return (
        db.query(Competitor)
        .filter(Competitor.workspace_id == workspace_id, Competitor.is_own_site.is_(True))
        .first()
    )


def get_own_site_surface(db: Session, workspace_id: int) -> Surface | None:
    own_site = get_own_site(db, workspace_id)
    if own_site is None:
        return None

    return (
        db.query(Surface)
        .filter(Surface.competitor_id == own_site.id)
        .order_by(Surface.id.asc())
        .first()
    )


def set_own_site(db: Session, workspace_id: int, url: str, created_by_user_id: int) -> Competitor:
    """Upsert — at most one own-site competitor per workspace. Reuses the
    exact same Competitor/Surface pipeline as a regular competitor (one
    hidden Competitor flagged is_own_site=True, one Surface) so every
    existing check/diff/scoring code path (run_surface_check, the
    scheduler, materiality scoring) works on it unchanged.
    """

    own_site = get_own_site(db, workspace_id)

    if own_site is None:
        own_site = Competitor(
            workspace_id=workspace_id,
            created_by_user_id=created_by_user_id,
            name="Your website",
            is_own_site=True,
        )
        db.add(own_site)
        db.flush()

        surface = Surface(
            competitor_id=own_site.id,
            surface_type="other",
            url=url,
            check_frequency="daily",
            capture_visual=False,
        )
        db.add(surface)
        db.commit()
        db.refresh(surface)
        schedule_surface(surface)
    else:
        surface = (
            db.query(Surface)
            .filter(Surface.competitor_id == own_site.id)
            .order_by(Surface.id.asc())
            .first()
        )
        if surface is not None:
            unschedule_surface(surface.id)
            surface.url = url
            db.commit()
            db.refresh(surface)
            schedule_surface(surface)

    db.refresh(own_site)
    return own_site


def delete_own_site(db: Session, workspace_id: int) -> bool:
    """Deletes the own-site competitor and everything that can accumulate
    under it through the normal automated check pipeline (change_embeddings
    -> briefing_change_logs links -> change_logs -> check_runs -> snapshots
    -> surfaces -> competitor), in strict child-before-parent order.

    Each step is flushed separately rather than batched into one flush/
    commit — against real Postgres (unlike SQLite's more lenient default FK
    enforcement, which let an earlier, under-tested version of this
    function slip through in the test suite), issuing deletes across
    multiple dependency levels in a single flush does not reliably order
    them by the FK graph and can violate a child table's constraint.

    Battlecards, company profiles, response-library items, and traffic
    snapshots are intentionally not cleaned up here — nothing in this
    codebase ever attaches those to a hidden is_own_site competitor (they
    all require an explicit API call the UI never makes against an id it
    never exposes), so there is nothing for those tables to have.
    """

    own_site = get_own_site(db, workspace_id)
    if own_site is None:
        return False

    surface_ids = [
        row[0]
        for row in db.query(Surface.id).filter(Surface.competitor_id == own_site.id).all()
    ]

    if surface_ids:
        change_log_ids = [
            row[0]
            for row in db.query(ChangeLog.id).filter(ChangeLog.surface_id.in_(surface_ids)).all()
        ]

        if change_log_ids:
            db.query(ChangeEmbedding).filter(
                ChangeEmbedding.change_log_id.in_(change_log_ids)
            ).delete(synchronize_session=False)
            db.execute(
                briefing_change_logs.delete().where(
                    briefing_change_logs.c.change_log_id.in_(change_log_ids)
                )
            )
            db.flush()

            db.query(ChangeLog).filter(ChangeLog.id.in_(change_log_ids)).delete(
                synchronize_session=False
            )
            db.flush()

        db.query(CheckRun).filter(CheckRun.surface_id.in_(surface_ids)).delete(
            synchronize_session=False
        )
        db.query(Snapshot).filter(Snapshot.surface_id.in_(surface_ids)).delete(
            synchronize_session=False
        )
        db.flush()

    surfaces = db.query(Surface).filter(Surface.competitor_id == own_site.id).all()
    for surface in surfaces:
        unschedule_surface(surface.id)
        db.delete(surface)
    db.flush()

    db.delete(own_site)
    db.commit()
    return True
