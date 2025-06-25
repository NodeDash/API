#!/usr/bin/env python3
"""
Redis client for updating device status from FastAPI endpoints.
This client can be imported and used in any FastAPI endpoint to update Redis
when device data is received.
"""

import redis
import logging
import secrets
from app.core.config import settings
from app.models.device import DeviceStatus
from typing import Optional

logger = logging.getLogger(__name__)

# Redis key prefix (must match the one used in redis_manager.py)
DEVICE_STATUS_KEY_PREFIX = "device:status:"
PASSWORD_RESET_PREFIX = "password_reset:"
MFA_SESSION_PREFIX = "mfa_session:"
EMAIL_VERIFICATION_PREFIX = "email_verification:"


class RedisClient:
    """Redis client for device status management in FastAPI endpoints."""

    _instance = None

    @classmethod
    def get_instance(cls):
        """Get or create a singleton instance of the RedisClient."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        """Initialize Redis connection using settings."""
        self.redis = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            password=settings.REDIS_PASSWORD,
            decode_responses=True,
        )
        logger.info(
            f"Redis client initialized: {settings.REDIS_HOST}:{settings.REDIS_PORT}/db{settings.REDIS_DB}"
        )

    def set_device_online(self, device_id: int, ttl_seconds: int) -> bool:
        """
        Mark a device as online by setting a Redis key with TTL.

        Args:
            device_id: Unique identifier for the device
            ttl_seconds: Time-to-live in seconds before the device is considered offline

        Returns:
            bool: Success status
        """
        key = f"{DEVICE_STATUS_KEY_PREFIX}{device_id}"
        try:
            self.redis.setex(key, ttl_seconds, DeviceStatus.ONLINE)
            logger.debug(f"Device {device_id} set online with TTL of {ttl_seconds}s")
            return True
        except redis.exceptions.RedisError as e:
            logger.error(f"Error setting device {device_id} online: {e}")
            return False

    def get_device_status(self, device_id: int) -> Optional[str]:
        """
        Get current device status from Redis.

        Args:
            device_id: Unique identifier for the device

        Returns:
            str: Device status or None if not found in Redis
        """
        key = f"{DEVICE_STATUS_KEY_PREFIX}{device_id}"
        try:
            if self.redis.exists(key):
                return DeviceStatus.ONLINE
            else:
                return DeviceStatus.OFFLINE
        except redis.exceptions.RedisError as e:
            logger.error(f"Error getting status for device {device_id}: {e}")
            return None

    def generate_and_store_verification_code(
        self, email: str, ttl_seconds: int = 900
    ) -> Optional[str]:
        """
        Generate a verification code for password reset, store it in Redis,
        and return the code.

        Args:
            email: User's email address
            ttl_seconds: Time-to-live in seconds for the verification code (default: 15 minutes)

        Returns:
            str: The generated verification code, or None if there was an error
        """
        try:
            # Generate a random 6-digit code
            code = "".join(secrets.choice("0123456789") for _ in range(6))

            # Store the code with the email as key
            key = f"{PASSWORD_RESET_PREFIX}{email}"
            self.redis.setex(key, ttl_seconds, code)

            logger.info(
                f"Generated verification code for {email} with TTL of {ttl_seconds}s"
            )
            return code
        except redis.exceptions.RedisError as e:
            logger.error(f"Error generating verification code for {email}: {e}")
            return None

    def verify_reset_code(self, email: str, code: str) -> bool:
        """
        Verify if the provided code matches the stored code for the given email.

        Args:
            email: User's email address
            code: Verification code to validate

        Returns:
            bool: True if the code is valid, False otherwise
        """
        key = f"{PASSWORD_RESET_PREFIX}{email}"
        try:
            stored_code = self.redis.get(key)
            if stored_code and stored_code == code:
                # Delete the code after successful verification to prevent reuse
                self.redis.delete(key)
                logger.info(f"Successfully verified code for {email}")
                return True
            logger.warning(f"Invalid verification code for {email}")
            return False
        except redis.exceptions.RedisError as e:
            logger.error(f"Error verifying code for {email}: {e}")
            return False

    # MFA Related Methods
    def store_mfa_session(
        self,
        user_id: int,
        email: str,
        remember_me: bool = False,
        ttl_seconds: int = 300,
    ) -> str:
        """
        Create and store a session ID for MFA verification.

        Args:
            user_id: User ID for the MFA session
            email: User's email address
            remember_me: Whether to use extended token expiration time
            ttl_seconds: Time-to-live for the session (default: 5 minutes)

        Returns:
            str: The session ID
        """
        try:
            # Generate a random session ID
            session_id = secrets.token_urlsafe(32)

            # Store the session with user data
            key = f"{MFA_SESSION_PREFIX}{session_id}"
            data = {"user_id": user_id, "email": email, "remember_me": remember_me}
            self.redis.setex(key, ttl_seconds, str(data))

            logger.info(f"Created MFA session for user {user_id}")
            return session_id
        except redis.exceptions.RedisError as e:
            logger.error(f"Error creating MFA session for user {user_id}: {e}")
            return None

    def verify_mfa_session(self, session_id: str) -> Optional[dict]:
        """
        Verify if an MFA session is valid and return the associated user data.

        Args:
            session_id: The MFA session ID to verify

        Returns:
            dict: User data associated with the session, or None if invalid
        """
        key = f"{MFA_SESSION_PREFIX}{session_id}"
        try:
            data = self.redis.get(key)
            if data:
                # Parse the stored string back to dict
                import ast

                user_data = ast.literal_eval(data)
                return user_data
            return None
        except redis.exceptions.RedisError as e:
            logger.error(f"Error verifying MFA session {session_id}: {e}")
            return None

    def clear_mfa_session(self, session_id: str) -> bool:
        """
        Delete an MFA session after it's been used.

        Args:
            session_id: The MFA session ID to delete

        Returns:
            bool: True if deleted successfully, False otherwise
        """
        key = f"{MFA_SESSION_PREFIX}{session_id}"
        try:
            self.redis.delete(key)
            logger.debug(f"Cleared MFA session {session_id}")
            return True
        except redis.exceptions.RedisError as e:
            logger.error(f"Error clearing MFA session {session_id}: {e}")
            return False

    # Email verification methods
    def generate_email_verification_code(
        self, email: str, ttl_seconds: int = 86400
    ) -> Optional[str]:
        """
        Generate and store a verification code for email verification.

        Args:
            email: User's email address
            ttl_seconds: Time-to-live in seconds for the verification code (default: 24 hours)

        Returns:
            str: The generated verification code, or None if there was an error
        """
        try:
            # Generate a random 6-digit code
            code = "".join(secrets.choice("0123456789") for _ in range(6))

            # Store the code with the email as key
            key = f"{EMAIL_VERIFICATION_PREFIX}{email}"
            self.redis.setex(key, ttl_seconds, code)

            logger.info(
                f"Generated email verification code for {email} with TTL of {ttl_seconds}s"
            )
            return code
        except redis.exceptions.RedisError as e:
            logger.error(f"Error generating email verification code for {email}: {e}")
            return None

    def verify_email_code(self, email: str, code: str) -> bool:
        """
        Verify if the provided email verification code matches the stored code.

        Args:
            email: User's email address
            code: Verification code to validate

        Returns:
            bool: True if the code is valid, False otherwise
        """
        key = f"{EMAIL_VERIFICATION_PREFIX}{email}"
        try:
            stored_code = self.redis.get(key)
            if stored_code and stored_code == code:
                # Delete the code after successful verification to prevent reuse
                self.redis.delete(key)
                logger.info(f"Successfully verified email code for {email}")
                return True
            logger.warning(f"Invalid email verification code for {email}")
            return False
        except redis.exceptions.RedisError as e:
            logger.error(f"Error verifying email code for {email}: {e}")
            return False
