from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, JSON, ForeignKey
from app.base import Base


class ChangeEmbedding(Base):
    """Stores each ChangeLog's embedding as a plain JSON float array with
    similarity computed in Python (see services/synthesis.py), rather than
    a pgvector column — the `vector` Postgres extension isn't available on
    this deployment's Postgres instance. Fine at this data volume; if this
    ever needs to scale, swap this table for a pgvector-backed one and
    replace the Python cosine-similarity loop with an indexed SQL query.
    """

    __tablename__ = "change_embeddings"

    id = Column(Integer, primary_key=True, index=True)

    change_log_id = Column(
        Integer,
        ForeignKey("change_logs.id"),
        nullable=False,
        unique=True
    )

    workspace_id = Column(
        Integer,
        ForeignKey("workspaces.id"),
        nullable=False
    )

    vector = Column(JSON, nullable=False)
    model = Column(String, nullable=False)

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )
