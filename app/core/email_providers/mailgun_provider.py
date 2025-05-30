"""
Mailgun email provider implementation.
"""

import logging
import requests
from typing import Dict, Any, Optional

from app.core.config import settings
from app.core.email_providers import EmailProvider

logger = logging.getLogger(__name__)


class MailgunEmailProvider(EmailProvider):
    """Mailgun email provider."""

    def __init__(self):
        self.api_key = getattr(settings, "MAILGUN_API_KEY", "")
        self.domain = getattr(settings, "MAILGUN_DOMAIN", "")
        self.base_url = getattr(
            settings, "MAILGUN_BASE_URL", "https://api.mailgun.net/v3"
        )
        self.from_email = getattr(settings, "FROM_EMAIL", "noreply@example.com")
        self.from_name = getattr(settings, "FROM_NAME", "")

        # Set region-specific base URL
        region = getattr(settings, "MAILGUN_REGION", "").lower()
        if region == "eu":
            self.base_url = "https://api.eu.mailgun.net/v3"

        # Format from address with name if provided
        if self.from_name:
            self.from_address = f"{self.from_name} <{self.from_email}>"
        else:
            self.from_address = self.from_email

    def send_email(
        self, to_email: str, subject: str, body: str, html_body: str = None
    ) -> bool:
        """
        Send an email using Mailgun API.

        Args:
            to_email: Recipient's email address
            subject: Email subject
            body: Plain text email body
            html_body: Optional HTML email body

        Returns:
            bool: True if the email was sent successfully, False otherwise
        """
        try:
            url = f"{self.base_url}/{self.domain}/messages"

            data: Dict[str, Any] = {
                "from": self.from_address,
                "to": to_email,
                "subject": subject,
                "text": body,
            }

            if html_body:
                data["html"] = html_body

            response = requests.post(url, auth=("api", self.api_key), data=data)

            if response.status_code == 200:
                logger.info(f"Email sent to {to_email} via Mailgun")
                return True
            else:
                logger.error(
                    f"Failed to send email via Mailgun: {response.status_code} - {response.text}"
                )
                return False

        except Exception as e:
            logger.error(f"Failed to send email to {to_email} via Mailgun: {e}")
            return False
