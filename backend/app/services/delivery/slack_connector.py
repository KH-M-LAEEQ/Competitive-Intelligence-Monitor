import requests

from app.services.delivery.base import DeliveryConnector, DeliveryPayload, DeliveryResult

_TIMEOUT_SECONDS = 10


class SlackConnector(DeliveryConnector):
    """Uses an incoming webhook URL — no OAuth app registration needed,
    unlike a full Slack app install.
    """

    def send(self, config: dict, payload: DeliveryPayload) -> DeliveryResult:
        webhook_url = (config or {}).get("webhook_url")
        if not webhook_url:
            return DeliveryResult(success=False, detail="No webhook_url configured")

        text = f"*{payload.title}*\n\n{payload.body_markdown}"

        try:
            response = requests.post(webhook_url, json={"text": text}, timeout=_TIMEOUT_SECONDS)
            response.raise_for_status()
        except requests.RequestException as exc:
            return DeliveryResult(success=False, detail=str(exc))

        return DeliveryResult(success=True)
