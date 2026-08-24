from datetime import datetime

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON
from app.base import Base


class Snapshot(Base):
    __tablename__ = "snapshots"

    id = Column(Integer, primary_key=True, index=True)

    surface_id = Column(
        Integer,
        ForeignKey("surfaces.id"),
        nullable=False
    )

    text_content = Column(Text, nullable=True)
    content_hash = Column(String, nullable=True, index=True)
    screenshot_path = Column(String, nullable=True)

    # LLM-generated plain-English read of this snapshot, populated only for
    # a surface's first ("baseline") capture — the one case where there's
    # no diff to summarize instead. Null when no LLM is configured or the
    # call fails; the raw text_content is always the fallback. Superseded
    # by headline/facts below for the current UI, but left in place rather
    # than migrated/dropped since older rows may still have them set.
    summary = Column(Text, nullable=True)
    highlights = Column(JSON, nullable=True)

    # Short 1-3 word tag (e.g. "Sale", "Pricing") plus a handful of
    # structured label/value facts actually stated on the page (counts,
    # price ranges, policies) — what the baseline card renders instead of
    # prose. Empty facts list is expected for pages with nothing concrete
    # to extract; the frontend falls back to a short raw-text preview then.
    headline = Column(String, nullable=True)
    facts = Column(JSON, nullable=True)

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )
