import enum
from datetime import datetime

from sqlalchemy import Column, Integer, Boolean, DateTime, JSON, Enum, ForeignKey, UniqueConstraint
from app.base import Base


class IntegrationProvider(str, enum.Enum):
    slack = "slack"
    email = "email"
    crm = "crm"


class WorkspaceIntegration(Base):
    """One row per (workspace, provider) — a workspace has at most one
    Slack webhook, one email recipient config, one CRM config. `config`
    shape depends on provider: Slack -> {"webhook_url"}, email ->
    {"to_email"}, CRM -> provider-specific (not yet implemented, see
    services/delivery/crm_connector.py).
    """

    __tablename__ = "workspace_integrations"
    __table_args__ = (
        UniqueConstraint("workspace_id", "provider", name="uq_workspace_integration_provider"),
    )

    id = Column(Integer, primary_key=True, index=True)

    workspace_id = Column(
        Integer,
        ForeignKey("workspaces.id"),
        nullable=False
    )

    provider = Column(Enum(IntegrationProvider), nullable=False)
    config = Column(JSON, nullable=False, default=dict)
    enabled = Column(Boolean, nullable=False, default=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
