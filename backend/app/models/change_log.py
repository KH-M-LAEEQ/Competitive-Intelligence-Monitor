from sqlalchemy import Column, Integer, String, Text, DateTime, Float, JSON, ForeignKey
from datetime import datetime
from app.base import Base


class ChangeLog(Base):
    __tablename__ = "change_logs"

    id = Column(Integer, primary_key=True, index=True)

    competitor_id = Column(
        Integer,
        ForeignKey("competitors.id"),
        nullable=False
    )

    surface_id = Column(
        Integer,
        ForeignKey("surfaces.id"),
        nullable=False
    )

    old_snapshot_id = Column(
        Integer,
        ForeignKey("snapshots.id"),
        nullable=True
    )

    new_snapshot_id = Column(
        Integer,
        ForeignKey("snapshots.id"),
        nullable=False
    )

    diff = Column(Text)

    materiality_score = Column(Integer)

    classification = Column(String)

    rationale = Column(Text)

    highlights = Column(JSON, nullable=True)

    # Short 1-3 word tag (e.g. "Sale", "Pricing") for the card title, and a
    # structured before/after read of the diff — both null until the LLM
    # call in check_service._apply_materiality_scoring succeeds. The
    # frontend falls back to the plain classification/rationale card when
    # `items` is empty, since not every diff is item/price-shaped.
    headline = Column(String, nullable=True)
    items = Column(JSON, nullable=True)

    visual_diff_score = Column(Float, nullable=True)

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )