from typing import List, Optional, Dict, Any, Union
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.models.provider import Provider, ProviderType
from app.models.enums import OwnerType
from app.schemas.provider import ProviderCreate, ProviderUpdate
from app.crud import chirpstack


def get_provider(db: Session, provider_id: int) -> Optional[Provider]:
    return db.query(Provider).filter(Provider.id == provider_id).first()


def get_providers(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    owner_id: Optional[int] = None,
    provider_type: Optional[ProviderType] = None,
    is_active: Optional[bool] = None,
    team_id: Optional[int] = None,
) -> List[Provider]:
    query = db.query(Provider)

    # If team_id is provided, filter by team ownership
    if team_id is not None:
        query = query.filter(
            Provider.owner_id == team_id, Provider.owner_type == OwnerType.TEAM
        )
    else:
        # Apply standard owner_id and owner_type filters if team_id not provided
        if owner_id is not None:
            query = query.filter(
                Provider.owner_id == owner_id, Provider.owner_type == OwnerType.USER
            )

    if provider_type is not None:
        query = query.filter(Provider.provider_type == provider_type)

    if is_active is not None:
        query = query.filter(Provider.is_active == is_active)

    result = query.offset(skip).limit(limit).all()
    return result


def get_provider_by_owner(
    db: Session,
    owner_id: int,
    owner_type: OwnerType,
    provider_type: ProviderType = None,
) -> Optional[Provider]:
    query = db.query(Provider).filter(
        Provider.owner_id == owner_id, Provider.owner_type == owner_type
    )

    if provider_type is not None:
        query = query.filter(Provider.provider_type == provider_type)

    return query.first()


def create_provider(db: Session, provider: ProviderCreate) -> Provider:
    """
    Create a new provider.
    """
    # Check if the provider already exists for the user
    existing_provider = get_provider_by_owner(
        db, owner_id=provider.owner_id, owner_type=provider.owner_type
    )
    if existing_provider and existing_provider.name == provider.name:
        raise HTTPException(
            status_code=400,
            detail="Provider with this name already exists for this user/team.",
        )

    # check if there is a provider for this type already
    if existing_provider and existing_provider.provider_type == provider.provider_type:
        raise HTTPException(
            status_code=400,
            detail="Provider already exists for this user/team with the same type.",
        )

    # Ensure we use the correct enum value by using the enum itself
    # This ensures the enum's string value (lowercase) is used rather than the name (uppercase)
    provider_data = provider.model_dump()
    db_provider = Provider(**provider_data)

    # use the enum value directly for provider_type
    if provider.provider_type == ProviderType.chirpstack:
        db_provider.provider_type = ProviderType.chirpstack
    elif provider.provider_type == ProviderType.email:
        db_provider.provider_type = ProviderType.email
    elif provider.provider_type == ProviderType.sms:
        db_provider.provider_type = ProviderType.sms
    else:
        # If the provider type is not recognized, raise an error
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported provider type: {provider.provider_type}",
        )

    db.add(db_provider)
    db.commit()
    db.refresh(db_provider)

    # If the provider type is chirpstack, run the setup code to ensure the provider is configured correctly
    if provider.provider_type == ProviderType.chirpstack:
        chirpstack.run_setup(db, provider=db_provider)

    return db_provider


def update_provider(
    db: Session, provider_id: int, provider_update: ProviderUpdate
) -> Provider:
    db_provider = get_provider(db, provider_id)
    if not db_provider:
        raise HTTPException(status_code=404, detail="Provider not found")

    update_data = provider_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_provider, field, value)

    # If the provider type is changed to chirpstack, run the setup code to ensure the provider is configured correctly
    if provider_update.provider_type == ProviderType.chirpstack:
        chirpstack.run_setup(db, provider=db_provider)

    db.add(db_provider)
    db.commit()
    db.refresh(db_provider)
    return db_provider


def delete_provider(db: Session, provider_id: int) -> bool:
    db_provider = get_provider(db, provider_id)
    if not db_provider:
        raise HTTPException(status_code=404, detail="Provider not found")

    db.delete(db_provider)
    db.commit()
    return True


def check_provider_ownership(
    db: Session, provider_id: int, user_id: int, user_teams: List[int]
) -> bool:
    """
    Check if a user has access to a provider through direct ownership or team membership.
    """
    db_provider = get_provider(db, provider_id)
    if not db_provider:
        return False

    # Check if user is the direct owner
    if db_provider.owner_type == OwnerType.USER and db_provider.owner_id == user_id:
        return True

    # Check if user is part of the team that owns the provider
    if db_provider.owner_type == OwnerType.TEAM and db_provider.owner_id in user_teams:
        return True

    return False
