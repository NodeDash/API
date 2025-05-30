# Password reset models
from pydantic import BaseModel, EmailStr
from typing import Optional


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetVerify(BaseModel):
    email: EmailStr
    code: str
    new_password: str


# Email verification models
class EmailVerificationRequest(BaseModel):
    """Request to send a verification email."""

    email: EmailStr


class EmailVerificationVerify(BaseModel):
    """Request to verify an email using a code."""

    email: EmailStr
    code: str


class EmailVerificationResponse(BaseModel):
    """Response for email verification status."""

    verified: bool
    message: str


# MFA models
class MFASetupRequest(BaseModel):
    """Request for setting up MFA."""

    pass


class MFASetupResponse(BaseModel):
    """Response with MFA setup data."""

    provisioning_uri: str
    secret: str
    qrcode: str


class MFAVerifyRequest(BaseModel):
    """Request for validating a MFA code."""

    code: str


class MFAVerifyResponse(BaseModel):
    """Response for MFA verification."""

    success: bool


class MFALoginRequest(BaseModel):
    """Request for logging in with MFA."""

    email: Optional[EmailStr] = None
    username: Optional[str] = None
    mfa_code: str
    session_id: str


class MFAStatusResponse(BaseModel):
    """Response with MFA status information."""

    enabled: bool
