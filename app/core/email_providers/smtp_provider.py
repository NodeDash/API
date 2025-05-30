"""
SMTP email provider implementation.
"""

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.core.config import settings
from app.core.email_providers import EmailProvider

logger = logging.getLogger(__name__)


class SMTPEmailProvider(EmailProvider):
    """SMTP email provider."""

    def __init__(self):
        self.smtp_host = getattr(settings, "SMTP_HOST", "localhost")
        self.smtp_port = getattr(settings, "SMTP_PORT", 25)
        self.smtp_user = getattr(settings, "SMTP_USER", "")
        self.smtp_password = getattr(settings, "SMTP_PASSWORD", "")
        self.from_email = getattr(settings, "FROM_EMAIL", "noreply@example.com")

    def send_email(
        self, to_email: str, subject: str, body: str, html_body: str = None
    ) -> bool:
        """
        Send an email using SMTP.

        Args:
            to_email: Recipient's email address
            subject: Email subject
            body: Plain text email body
            html_body: Optional HTML email body

        Returns:
            bool: True if the email was sent successfully, False otherwise
        """
        try:
            # Create message
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.from_email
            msg["To"] = to_email

            # Add text part
            msg.attach(MIMEText(body, "plain"))

            # Add HTML part if provided
            if html_body:
                msg.attach(MIMEText(html_body, "html"))

            # Connect to server
            server = smtplib.SMTP(self.smtp_host, self.smtp_port)

            # Use TLS if available
            try:
                server.starttls()
            except Exception as e:
                logger.warning(f"Could not start TLS: {e}")

            # Login if credentials are provided
            if self.smtp_user and self.smtp_password:
                server.login(self.smtp_user, self.smtp_password)

            # Send email
            server.sendmail(self.from_email, to_email, msg.as_string())
            server.quit()
            logger.info(f"Email sent to {to_email} via SMTP")
            return True

        except Exception as e:
            logger.error(f"Failed to send email to {to_email} via SMTP: {e}")
            return False
