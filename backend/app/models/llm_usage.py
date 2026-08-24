import enum
from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, Enum, ForeignKey
from app.base import Base


class LLMUsagePurpose(str, enum.Enum):
    scoring = "scoring"
    classification = "classification"
    briefing = "briefing"
    embedding = "embedding"
    site_summary = "site_summary"
    category_price = "category_price"


class TokenUsageLog(Base):
    __tablename__ = "token_usage_logs"

    id = Column(Integer, primary_key=True, index=True)

    workspace_id = Column(
        Integer,
        ForeignKey("workspaces.id"),
        nullable=False
    )

    purpose = Column(Enum(LLMUsagePurpose), nullable=False)
    model = Column(String, nullable=False)

    prompt_tokens = Column(Integer, nullable=False, default=0)
    completion_tokens = Column(Integer, nullable=False, default=0)

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )
