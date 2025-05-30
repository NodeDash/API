from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.core.auth import (
    get_current_active_user,
    check_resource_permissions,
    check_team_membership,
)
from app.models.enums import OwnerType
from app.models.provider import ProviderType
from app.schemas.provider import Provider, ProviderCreate, ProviderUpdate
from app.crud import provider as provider_crud
from app.crud import team as crud_team

router = APIRouter()


@router.get("/", response_model=List[Provider])
def get_providers(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    provider_type: Optional[ProviderType] = None,
    is_active: Optional[bool] = None,
    team_id: Optional[int] = Query(None, description="Filter by team ID"),
    current_user=Depends(get_current_active_user),
):
    """
    Get providers based on ownership:
    - If team_id is specified, returns only providers owned by that team
    - Otherwise, returns only providers owned directly by the current user
    Optionally filter by provider type and active status.
    """

    # If team_id is provided, check that the user is a member of that team
    if team_id:
        # This will raise HTTPException if user is not a member
        check_team_membership(db, current_user, team_id)

        # Return only providers from the specified team using the team_id parameter
        return provider_crud.get_providers(
            db=db,
            skip=skip,
            limit=limit,
            team_id=team_id,
            provider_type=provider_type,
            is_active=is_active,
        )

    # If no team_id is specified, return only providers owned directly by the user
    return provider_crud.get_providers(
        db=db,
        skip=skip,
        limit=limit,
        owner_id=current_user.id,
        provider_type=provider_type,
        is_active=is_active,
    )


@router.post("/", response_model=Provider)
def create_provider(
    provider_in: ProviderCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    # if owner type is team, make sure the user is a member of the team
    if provider_in.owner_type == OwnerType.TEAM:
        # This will raise HTTPException if user is not a member
        check_team_membership(db, current_user, provider_in.owner_id)
    # If owner type is user, make sure the user is the owner
    elif provider_in.owner_type == OwnerType.USER:
        if provider_in.owner_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not enough permissions")
    # If owner type is not user or team, raise an error
    else:
        raise HTTPException(
            status_code=400, detail="Invalid owner type. Must be USER or TEAM."
        )

    # Create the provider
    return provider_crud.create_provider(db=db, provider=provider_in)


@router.get("/{provider_id}", response_model=Provider)
def get_provider(
    provider_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    """
    Get a specific provider by ID.
    """
    provider = provider_crud.get_provider(db=db, provider_id=provider_id)

    # Check permissions - will raise HTTPException if not allowed
    check_resource_permissions(db, current_user, provider, "access")

    return provider


@router.put("/{provider_id}", response_model=Provider)
def update_provider(
    provider_id: int,
    provider_in: ProviderUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    """
    Update a provider.

    If team_id is provided, provider ownership will be transferred to the team.
    """
    provider = provider_crud.get_provider(db=db, provider_id=provider_id)

    # Check permissions - will raise HTTPException if not allowed
    check_resource_permissions(db, current_user, provider, "update")

    return provider_crud.update_provider(
        db=db, provider_id=provider_id, provider_update=provider_in
    )


@router.delete("/{provider_id}", response_model=bool)
def delete_provider(
    provider_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    """
    Delete a provider.
    """
    provider = provider_crud.get_provider(db=db, provider_id=provider_id)

    # Check permissions - will raise HTTPException if not allowed
    check_resource_permissions(db, current_user, provider, "delete")

    return provider_crud.delete_provider(db=db, provider_id=provider_id)
