from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime
from app.base import Base


class Workspace(Base):
    __tablename__ = "workspaces"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String, nullable=False)
    slug = Column(String, unique=True, nullable=False, index=True)

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )
