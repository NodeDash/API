from datetime import timedelta
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Body, Form
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
import pyotp
import qrcode
import io
import base64
from app.schemas.auth import (
    PasswordResetRequest,
    PasswordResetVerify,
    EmailVerificationRequest,
    EmailVerificationVerify,
    EmailVerificationResponse,
    MFASetupRequest,
    MFASetupResponse,
    MFAVerifyRequest,
    MFAVerifyResponse,
    MFALoginRequest,
    MFAStatusResponse,
)

from app.core.config import settings
from app.core.security import (
    create_access_token,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    get_password_hash,
)
from app.core.auth import get_current_active_user
from app.core.email import send_password_reset_email, send_email_verification_email
from app.db.database import get_db
from app.models.user import User
from app.crud import user as user_crud
from app.schemas.user import User as UserSchema, UserCreate, Token
from app.redis.client import RedisClient

router = APIRouter()


class OAuth2PasswordRequestFormWithRememberMe(OAuth2PasswordRequestForm):
    def __init__(
        self,
        grant_type: str = Form(default=None, regex="password"),
        username: str = Form(),
        password: str = Form(),
        scope: str = Form(default=""),
        client_id: Optional[str] = Form(default=None),
        client_secret: Optional[str] = Form(default=None),
        remember_me: Optional[str] = Form(default="false"),
    ):
        super().__init__(
            grant_type=grant_type,
            username=username,
            password=password,
            scope=scope,
            client_id=client_id,
            client_secret=client_secret,
        )
        self.remember_me = remember_me


@router.post("/register", response_model=UserSchema)
def register(*, db: Session = Depends(get_db), user_in: UserCreate) -> Any:
    """
    Register a new user account.

    This endpoint creates a new user with the provided information.
    Email verification may be required based on system configuration.

    Parameters:
    - **db**: Database session dependency
    - **user_in**: User creation data including email, password, and other required fields

    Returns:
    - User object with generated ID and without sensitive information

    Notes:
    - Password is automatically hashed before storage
    - Newly registered users may need to verify their email before gaining full access

    Raises:
    - 400: If the email is already registered
    - 422: If the input data fails validation
    """
    """
    Register a new user and send a verification email.
    """
    user = user_crud.get_by_email(db, email=user_in.email)
    if user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email already exists",
        )

    user_by_username = user_crud.get_by_username(db, username=user_in.username)
    if user_by_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this username already exists",
        )

    # Create user with email_verified set to False
    user = user_crud.create(db, obj_in=user_in)

    # Generate and store email verification code
    redis_client = RedisClient.get_instance()
    verification_code = redis_client.generate_email_verification_code(user.email)

    if not verification_code:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate verification code",
        )

    # Send verification email
    email_sent = send_email_verification_email(user.email, verification_code)

    if not email_sent:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send verification email",
        )

    return user


@router.post("/login", response_model=Dict[str, Any])
def login(
    db: Session = Depends(get_db),
    form_data: OAuth2PasswordRequestFormWithRememberMe = Depends(),
) -> Any:
    """
    Authenticate a user and issue an access token.

    This endpoint validates user credentials and returns an authentication token
    that can be used for subsequent API calls. Compatible with OAuth2 password flow
    for Swagger UI authorization.

    Parameters:
    - **db**: Database session dependency
    - **form_data**: OAuth2PasswordRequestForm containing username and password

    Returns:
    - Authentication token and user information:
        - access_token: JWT token for API authentication
        - token_type: Token type (typically "bearer")
        - user: User object without sensitive information
        - requires_mfa: Boolean indicating if MFA verification is required

    Notes:
    - Username field accepts either email or username
    - Failed login attempts may be rate-limited
    - Multi-factor authentication may be required depending on user settings

    Raises:
    - 401: If credentials are invalid or account is locked
    - 403: If email verification is required but not completed
    """

    # Extract credentials from form data
    username_or_email = form_data.username
    password = form_data.password
    remember_me = form_data.remember_me

    # Determine if it's an email or username
    email = username_or_email if "@" in username_or_email else None
    username = username_or_email if "@" not in username_or_email else None

    # Convert remember_me string to boolean
    remember_me_bool = (
        remember_me.lower() == "true"
        if isinstance(remember_me, str)
        else bool(remember_me)
    )

    if not username_or_email or not password:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Username/email and password are required",
        )

    # Call authenticate with correct parameters
    user = user_crud.authenticate(db, email=email, username=username, password=password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email/username or password",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inactive user",
        )
    if not user.email_verified:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email not verified",
        )

    # If MFA is enabled for the user, return a session ID instead of a token
    if user.mfa_enabled:
        # Store a temporary session for MFA verification
        redis_client = RedisClient.get_instance()

        session_id = redis_client.store_mfa_session(
            user.id, user.email, remember_me=remember_me_bool
        )

        return {"mfa_required": True, "session_id": session_id, "email": user.email}

    # if remember me is true, set expiration to 30 days, otherwise use default
    if remember_me_bool:
        ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES_REMEMBER_ME
    else:
        ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES

    # Create access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        subject=user.id, expires_delta=access_token_expires
    )

    return {"access_token": access_token, "token_type": "bearer", "mfa_required": False}


@router.get("/verify", response_model=UserSchema)
def verify_token(current_user: User = Depends(get_current_active_user)) -> Any:
    """
    Verify the current authentication token and return user information.

    This endpoint validates the provided JWT token and returns the associated user details.
    Useful for checking token validity and retrieving current user information.

    Parameters:
    - **current_user**: User object from the token validation dependency

    Returns:
    - Current user object without sensitive information

    Notes:
    - Requires a valid JWT token in the Authorization header
    - Can be used for session validation and refreshing user data

    Raises:
    - 401: If the token is invalid, expired, or missing
    - 403: If the user account is inactive
    """
    """
    Verify access token and return user information if valid.
    This endpoint is used by client applications to check if a token is still valid.
    """
    return current_user


@router.post("/request-password-reset")
def request_password_reset(
    request_data: PasswordResetRequest, db: Session = Depends(get_db)
) -> Dict[str, str]:
    """
    Request a password reset for a user account.

    This endpoint initiates the password reset process by sending
    a reset link or code to the user's registered email address.

    Parameters:
    - **request_data**: Object containing the email address for the account
    - **db**: Database session dependency

    Returns:
    - Message confirming that reset instructions were sent

    Notes:
    - Always returns a success message even if the email doesn't exist (for security)
    - The reset link/code typically expires after a short period (e.g., 30 minutes)
    - Rate limiting may be applied to prevent abuse
    """
    """
    Request a password reset. This will send an email with a verification code
    if the email exists in the system.
    """
    user = user_crud.get_by_email(db, email=request_data.email)

    # Always return success, even if email doesn't exist (for security)
    # This prevents user enumeration attacks
    if not user:
        return {
            "status": "success",
            "message": "If your email is registered, you will receive a reset code",
        }

    # Generate and store verification code in Redis
    redis_client = RedisClient.get_instance()
    verification_code = redis_client.generate_and_store_verification_code(
        request_data.email
    )

    if not verification_code:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate verification code",
        )

    # Send email with verification code
    email_sent = send_password_reset_email(request_data.email, verification_code)

    if not email_sent:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send verification email",
        )

    return {
        "status": "success",
        "message": "If your email is registered, you will receive a reset code",
    }


@router.post("/reset-password")
def reset_password(
    reset_data: PasswordResetVerify, db: Session = Depends(get_db)
) -> Dict[str, str]:
    """
    Complete the password reset process with a verification token.

    This endpoint validates the reset token and updates the user's password
    if the token is valid and hasn't expired.

    Parameters:
    - **reset_data**: Object containing the reset token and new password
    - **db**: Database session dependency

    Returns:
    - Message confirming successful password reset

    Notes:
    - The reset token must match a previously requested reset
    - Tokens expire after a short period (typically 30 minutes)
    - Previous sessions will be invalidated after password reset

    Raises:
    - 400: If the token is invalid or expired
    - 422: If the new password doesn't meet security requirements
    """
    """
    Verify reset code and update the user's password.
    """
    # Check if user exists
    user = user_crud.get_by_email(db, email=reset_data.email)
    if not user:
        # Use a generic error message to prevent user enumeration
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification code",
        )

    # Verify the code
    redis_client = RedisClient.get_instance()
    is_valid = redis_client.verify_reset_code(reset_data.email, reset_data.code)

    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification code",
        )

    # Update the password
    hashed_password = get_password_hash(reset_data.new_password)
    user.hashed_password = hashed_password
    db.add(user)
    db.commit()

    return {"status": "success", "message": "Password has been reset successfully"}


@router.post("/verify-email", response_model=EmailVerificationResponse)
def verify_email(
    verification_data: EmailVerificationVerify, db: Session = Depends(get_db)
) -> Any:
    """
    Verify a user's email address using the verification code sent to their email.
    """
    # Check if user exists
    user = user_crud.get_by_email(db, email=verification_data.email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email address",
        )

    # If the email is already verified, return success
    if user.email_verified:
        return {"verified": True, "message": "Email already verified"}

    # Verify the code
    redis_client = RedisClient.get_instance()
    is_valid = redis_client.verify_email_code(
        verification_data.email, verification_data.code
    )

    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification code",
        )

    # Update the user's email_verified status
    user.email_verified = True
    db.add(user)
    db.commit()

    return {"verified": True, "message": "Email verified successfully"}


@router.post("/resend-verification-email", response_model=Dict[str, str])
def resend_verification_email(
    request_data: EmailVerificationRequest, db: Session = Depends(get_db)
) -> Any:
    """
    Resend the verification email to the user.
    """
    user = user_crud.get_by_email(db, email=request_data.email)

    # Always return success, even if email doesn't exist (for security)
    if not user:
        return {
            "status": "success",
            "message": "If your email is registered and not verified, you will receive a verification code",
        }

    # Don't send another email if already verified
    if user.email_verified:
        return {
            "status": "success",
            "message": "Email is already verified",
        }

    # Generate and store verification code in Redis
    redis_client = RedisClient.get_instance()
    verification_code = redis_client.generate_email_verification_code(
        request_data.email
    )

    if not verification_code:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate verification code",
        )

    # Send email with verification code
    email_sent = send_email_verification_email(request_data.email, verification_code)

    if not email_sent:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send verification email",
        )

    return {
        "status": "success",
        "message": "Verification email has been sent",
    }


@router.post("/mfa/verify-login", response_model=Token)
def verify_mfa_login(mfa_login: MFALoginRequest, db: Session = Depends(get_db)) -> Any:
    """
    Verify MFA code during login and return a token if successful.
    """
    # Verify that session exists
    redis_client = RedisClient.get_instance()
    session_data = redis_client.verify_mfa_session(mfa_login.session_id)

    if not session_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired MFA session",
        )

    user_id = session_data.get("user_id")
    user = user_crud.get(db, user_id=user_id)

    if not user or not user.mfa_enabled or not user.mfa_secret:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="MFA is not enabled for this user",
        )

    # Verify TOTP code
    totp = pyotp.TOTP(user.mfa_secret)
    if not totp.verify(mfa_login.mfa_code):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid MFA code",
        )

    # Clear the MFA session
    redis_client.clear_mfa_session(mfa_login.session_id)

    # Check if remember_me was set during login
    remember_me = session_data.get("remember_me", False)

    # Use appropriate token expiration based on remember_me setting
    if remember_me:
        access_token_expires = timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES_REMEMBER_ME
        )
    else:
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    # Generate access token
    access_token = create_access_token(
        subject=user.id, expires_delta=access_token_expires
    )

    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/mfa/setup", response_model=MFASetupResponse)
def setup_mfa(
    _: MFASetupRequest = Body(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> Any:
    """
    Set up MFA for the current user. Returns the secret and a QR code for Google Authenticator.
    """
    # Generate a new secret
    secret = pyotp.random_base32()

    # Create a provisioning URI for Google Authenticator
    totp = pyotp.TOTP(secret)
    app_name = settings.PROJECT_NAME
    provisioning_uri = totp.provisioning_uri(
        name=current_user.email, issuer_name=app_name
    )

    # Generate QR code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(provisioning_uri)
    qr.make(fit=True)

    # Convert QR code to base64 string for display in frontend
    img = qr.make_image(fill_color="black", back_color="white")
    buffered = io.BytesIO()
    img.save(buffered)
    img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")

    # Store the secret temporarily (not enabling MFA yet)
    current_user.mfa_secret = secret
    db.add(current_user)
    db.commit()

    return {
        "secret": secret,
        "provisioning_uri": provisioning_uri,
        "qrcode": f"data:image/png;base64,{img_str}",
    }


@router.post("/mfa/verify", response_model=MFAVerifyResponse)
def verify_mfa(
    verify_data: MFAVerifyRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> Any:
    """
    Verify the MFA code and enable MFA for the user if verification is successful.
    """
    if not current_user.mfa_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA setup not initiated",
        )

    # Verify the code
    totp = pyotp.TOTP(current_user.mfa_secret)
    if not totp.verify(verify_data.code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid MFA code",
        )

    # Enable MFA
    current_user.mfa_enabled = True
    db.add(current_user)
    db.commit()

    return {"success": True}


@router.post("/mfa/disable", response_model=MFAStatusResponse)
def disable_mfa(
    verify_data: MFAVerifyRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> Any:
    """
    Disable MFA for the user after verifying the code.
    """
    if not current_user.mfa_enabled or not current_user.mfa_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA is not enabled",
        )

    # Verify the code
    totp = pyotp.TOTP(current_user.mfa_secret)
    if not totp.verify(verify_data.code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid MFA code",
        )

    # Disable MFA
    current_user.mfa_enabled = False
    current_user.mfa_secret = None  # Clear the secret for security
    db.add(current_user)
    db.commit()

    return {"enabled": False}


@router.get("/mfa/status", response_model=MFAStatusResponse)
def mfa_status(current_user: User = Depends(get_current_active_user)) -> Any:
    """
    Get the current MFA status for the user.
    """
    return {"enabled": current_user.mfa_enabled}
