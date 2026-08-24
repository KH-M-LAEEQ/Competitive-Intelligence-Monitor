import re

from sqlalchemy.orm import Session

from app.models.workspace import Workspace


def unique_slug(db: Session, name: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "workspace"
    slug = base
    n = 2

    while db.query(Workspace).filter(Workspace.slug == slug).first() is not None:
        slug = f"{base}-{n}"
        n += 1

    return slug
