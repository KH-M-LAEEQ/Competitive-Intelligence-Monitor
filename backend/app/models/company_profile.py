from datetime import datetime

from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, ForeignKey
from app.base import Base


class CompanyProfile(Base):
    """Structured background on a competitor — gives the LLM context for
    its materiality judgments beyond just the raw diff. Manually maintained
    for now; LLM-assisted enrichment is a natural future addition, not
    built here.
    """

    __tablename__ = "company_profiles"

    id = Column(Integer, primary_key=True, index=True)

    competitor_id = Column(
        Integer,
        ForeignKey("competitors.id"),
        nullable=False,
        unique=True
    )

    industry = Column(String, nullable=True)
    hq_location = Column(String, nullable=True)
    employee_range = Column(String, nullable=True)
    funding_stage = Column(String, nullable=True)
    key_people = Column(JSON, nullable=True)
    notes_markdown = Column(Text, nullable=True)

    # Root domain used for traffic lookups (see traffic_service.py) — kept
    # separate from Surface.url, since surfaces point at specific pages to
    # diff for content changes, while traffic estimates are almost always
    # reported at the whole-domain level.
    website_domain = Column(String, nullable=True)

    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )
