"""
Base module for email providers.
"""

from abc import ABC, abstractmethod


class EmailProvider(ABC):
    """Base class for email providers."""

    @abstractmethod
    def send_email(
        self, to_email: str, subject: str, body: str, html_body: str = None
    ) -> bool:
        """
        Send an email.

        Args:
            to_email: Recipient's email address
            subject: Email subject
            body: Plain text email body
            html_body: Optional HTML email body

        Returns:
            bool: True if the email was sent successfully, False otherwise
        """
        pass
