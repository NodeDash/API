"""
Email utility module for sending emails to users.
"""

import logging

from app.core.config import settings
from app.core.email_providers import EmailProvider
from app.core.email_providers.smtp_provider import SMTPEmailProvider
from app.core.email_providers.mailgun_provider import MailgunEmailProvider
from app.models.enums import EmailMode

logger = logging.getLogger(__name__)


def get_email_provider() -> EmailProvider:
    """
    Get the appropriate email provider based on settings.

    Returns:
        EmailProvider: An instance of the configured email provider
    """
    email_mode = getattr(settings, "EMAIL_MODE", EmailMode.SMTP)

    if email_mode == EmailMode.MAILGUN:
        return MailgunEmailProvider()

    # Default to SMTP
    return SMTPEmailProvider()


def send_email(to_email: str, subject: str, body: str, html_body: str = None) -> bool:
    """
    Send an email using the configured email provider.

    Args:
        to_email: Recipient's email address
        subject: Email subject
        body: Plain text email body
        html_body: Optional HTML email body

    Returns:
        bool: True if the email was sent successfully, False otherwise
    """
    provider = get_email_provider()
    return provider.send_email(to_email, subject, body, html_body)


def send_password_reset_email(to_email: str, verification_code: str) -> bool:
    """
    Send a password reset email with verification code.

    Args:
        to_email: Recipient's email address
        verification_code: The verification code for password reset

    Returns:
        bool: True if the email was sent successfully, False otherwise
    """
    subject = "Password Reset Request"
    website_address = settings.WEBSITE_ADDRESS.rstrip("/")

    body = f"""
    Hello,
    
    We received a request to reset your password. Please use the following verification code to complete the process:
    
    {verification_code}
    
    This code will expire in 15 minutes.
    
    You can reset your password at: {website_address}/reset-password
    
    If you didn't request this, you can safely ignore this email.
    
    Best regards,
    The Device Manager Team
    """

    html_body = f"""
    <html>
      <body>
        <h2>Password Reset Request</h2>
        <p>Hello,</p>
        <p>We received a request to reset your password. Please use the following verification code to complete the process:</p>
        <div style="margin: 20px; padding: 10px; background-color: #f0f0f0; font-size: 24px; text-align: center; font-family: monospace;">
          <strong>{verification_code}</strong>
        </div>
        <p>This code will expire in 15 minutes.</p>
        <p><a href="{website_address}/reset-password">Click here</a> to reset your password or copy and paste this URL into your browser: {website_address}/reset-password</p>
        <p>If you didn't request this, you can safely ignore this email.</p>
        <p>Best regards,<br>The Device Manager Team</p>
      </body>
    </html>
    """

    return send_email(to_email, subject, body, html_body)


def send_email_verification_email(to_email: str, verification_code: str) -> bool:
    """
    Send an email verification email with verification code.

    Args:
        to_email: Recipient's email address
        verification_code: The verification code for email verification

    Returns:
        bool: True if the email was sent successfully, False otherwise
    """
    subject = "Verify Your Email Address"
    website_address = settings.WEBSITE_ADDRESS.rstrip("/")

    body = f"""
    Hello,
    
    Thank you for registering! Please verify your email address by using the following code:
    
    {verification_code}
    
    This code will expire in 24 hours.
    
    You can verify your email at: {website_address}/email-verify
    
    If you didn't register for an account, you can safely ignore this email.
    
    Best regards,
    The Device Manager Team
    """

    html_body = f"""
    <html>
      <body>
        <h2>Verify Your Email Address</h2>
        <p>Hello,</p>
        <p>Thank you for registering! Please verify your email address by using the following code:</p>
        <div style="margin: 20px; padding: 10px; background-color: #f0f0f0; font-size: 24px; text-align: center; font-family: monospace;">
          <strong>{verification_code}</strong>
        </div>
        <p>This code will expire in 24 hours.</p>
        <p><a href="{website_address}/email-verify">Click here</a> to verify your email or copy and paste this URL into your browser: {website_address}/email-verify</p>
        <p>If you didn't register for an account, you can safely ignore this email.</p>
        <p>Best regards,<br>The Device Manager Team</p>
      </body>
    </html>
    """

    return send_email(to_email, subject, body, html_body)
