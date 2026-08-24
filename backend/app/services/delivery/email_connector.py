import smtplib
from email.mime.text import MIMEText

from app.core.config import settings
from app.services.delivery.base import DeliveryConnector, DeliveryPayload, DeliveryResult

_TIMEOUT_SECONDS = 10


class EmailConnector(DeliveryConnector):
    def send(self, config: dict, payload: DeliveryPayload) -> DeliveryResult:
        to_email = (config or {}).get("to_email")
        if not to_email:
            return DeliveryResult(success=False, detail="No to_email configured")

        if not settings.smtp_host:
            return DeliveryResult(
                success=False, detail="SMTP is not configured on this deployment"
            )

        message = MIMEText(payload.body_markdown)
        message["Subject"] = payload.title
        message["From"] = settings.smtp_from_email or "noreply@example.com"
        message["To"] = to_email

        try:
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=_TIMEOUT_SECONDS) as server:
                server.starttls()
                if settings.smtp_user and settings.smtp_password:
                    server.login(settings.smtp_user, settings.smtp_password)
                server.send_message(message)
        except (smtplib.SMTPException, OSError) as exc:
            return DeliveryResult(success=False, detail=str(exc))

        return DeliveryResult(success=True)
