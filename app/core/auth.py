"""
Authentication module for JWT validation and API key validation.
"""

from fastapi import Depends, HTTPException, status, Header, Security
from fastapi.security import OAuth2PasswordBearer, APIKeyHeader
from jose import jwt, JWTError
from pydantic import ValidationError
from sqlalchemy.orm import Session
from typing import Any, Optional

from app.core.config import settings
from app.core.security import ALGORITHM
from app.db.database import get_db
from app.crud.user import get
from app.crud import provider as provider_crud
from app.crud import team as team_crud
from app.models.provider import ProviderType
from app.models.enums import OwnerType
from app.schemas.user import TokenPayload, User
from app.models.user import User as UserModel

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")

# Setup API Key authentication
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=True)


async def verify_api_key(
    api_key: str = Security(api_key_header), db: Session = Depends(get_db)
):
    """
    Verify the API key against ChirpStack provider API keys or the one in settings.

    Args:
        api_key: The API key from the request header
        db: Database session dependency

    Returns:
        bool: True if the API key is valid

    Raises:
        HTTPException: If the API key is invalid
    """
    # First check if any ChirpStack provider has this API key
    providers = provider_crud.get_providers(
        db=db, provider_type=ProviderType.chirpstack, is_active=True
    )

    for provider in providers:
        # Check if the provider configuration contains an X-API-KEY
        if provider.config and "X-API-KEY" in provider.config:
            if provider.config["X-API-KEY"] == api_key:
                return True

    # Fall back to the settings SECRET_KEY if no provider match
    if api_key == settings.SECRET_KEY:
        return True

    # If neither match, raise an exception
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Invalid API key",
    )


async def get_current_user(
    db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)
) -> User:
    """
    Get the current authenticated user from the JWT token.

    Args:
        db: Database session dependency
        token: JWT token extracted from the request

    Returns:
        The authenticated user

    Raises:
        HTTPException: If the token is invalid or the user doesn't exist
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        token_data = TokenPayload(**payload)
    except (JWTError, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
        )

    user = get(db, user_id=int(token_data.sub))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return user


async def get_current_active_user(
    current_user: UserModel = Depends(get_current_user),
) -> UserModel:
    """
    Get the current active user.

    Args:
        current_user: The current authenticated user

    Returns:
        The current active user

    Raises:
        HTTPException: If the user is not active
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user",
        )
    return current_user


async def get_current_superuser(
    current_user: UserModel = Depends(get_current_user),
) -> UserModel:
    """
    Get the current superuser.

    Args:
        current_user: The current authenticated user

    Returns:
        The current superuser

    Raises:
        HTTPException: If the user is not a superuser
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
    return current_user


def check_resource_permissions(
    db: Session,
    current_user: UserModel,
    resource: Any,
    action_name: str = "access",
    check_not_found: bool = True,
    error_status_code: int = status.HTTP_403_FORBIDDEN,
) -> bool:
    """
    Check if a user has permission to perform an action on a resource.
    This centralizes permission checks for resources with owner_id and owner_type attributes.

    Args:
        db: Database session
        current_user: Current authenticated user
        resource: The resource to check permissions for (must have owner_id and owner_type attributes)
        action_name: Name of the action being performed (for error message)
        check_not_found: Whether to raise an exception if the resource is None
        error_status_code: HTTP status code to use for permission errors

    Returns:
        True if the user has permission to access the resource

    Raises:
        HTTPException: If the resource is not found or the user doesn't have permission
    """
    # Handle None resource (not found case)
    if resource is None:
        if check_not_found:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"Resource not found"
            )
        return False

    # Superusers have access to everything
    if current_user.is_superuser:
        return True

    # Check if the user owns the resource directly
    if resource.owner_type == OwnerType.USER and resource.owner_id == current_user.id:
        return True

    # Check if the user is a member of the team that owns the resource
    if resource.owner_type == OwnerType.TEAM:
        is_member = team_crud.is_user_in_team(
            db, team_id=resource.owner_id, user_id=current_user.id
        )
        if is_member:
            return True

    # If we get here, the user doesn't have permission
    raise HTTPException(
        status_code=error_status_code,
        detail=f"Not enough permissions to {action_name} this resource",
    )


# Helper function to check if a user is in a specific team
def check_team_membership(
    db: Session, current_user: UserModel, team_id: int, raise_exception: bool = True
) -> bool:
    """
    Check if a user is a member of a specific team.

    Args:
        db: Database session
        current_user: Current authenticated user
        team_id: ID of the team to check membership for
        raise_exception: Whether to raise an exception if the user is not a member

    Returns:
        True if the user is a member of the team, False otherwise

    Raises:
        HTTPException: If raise_exception is True and the user is not a member
    """
    # Superusers have access to all teams
    if current_user.is_superuser:
        return True

    is_member = team_crud.is_user_in_team(db, team_id=team_id, user_id=current_user.id)

    if not is_member and raise_exception:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not a member of this team"
        )

    return is_member


# Dependencies for different auth levels
jwt_auth = Depends(get_current_active_user)
superuser_auth = Depends(get_current_superuser)
api_key_auth = Depends(verify_api_key)
