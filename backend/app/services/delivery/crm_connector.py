from app.services.delivery.base import DeliveryConnector, DeliveryPayload, DeliveryResult


class CRMConnector(DeliveryConnector):
    """Stub. Real CRM delivery (Salesforce/HubSpot) needs an OAuth app
    registered in each provider's developer console — a manual step outside
    what a coding agent can do blind. Wire a real implementation in once
    those credentials exist; the interface (send(config, payload)) is
    already in place for it.
    """

    def send(self, config: dict, payload: DeliveryPayload) -> DeliveryResult:
        return DeliveryResult(success=False, detail="CRM delivery is not yet implemented")
