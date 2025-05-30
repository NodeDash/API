from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app import crud, schemas
from app.core.auth import jwt_auth, check_resource_permissions, check_team_membership
from app.db.database import get_db
from app.models.user import User
from app.models.integration import Integration
from app.models.integration_history import IntegrationHistory
from app.models.enums import OwnerType
from app.crud import team as crud_team

router = APIRouter()


# all-history
@router.get(
    "/all-history",
    response_model=List[schemas.integration_history.IntegrationHistory],
    dependencies=[jwt_auth],
)
def read_user_integration_history(
    *,
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    team_id: Optional[int] = Query(None, description="Filter by team ID"),
    current_user: User = jwt_auth
) -> Any:
    """
    Get all integration history.

    If team_id is provided, returns history for integrations owned by that team.
    Otherwise, returns history for integrations owned by the current user and their teams.
    """
    if current_user.is_superuser:
        # Get all integrations if superuser
        integrations = crud.integration.get_integrations(db=db)
    elif team_id:
        # Check if user is a member of the team
        check_team_membership(db, current_user, team_id)

        # Get integrations belonging to the specified team
        integrations = crud.integration.get_integrations(db=db, team_id=team_id)
    else:
        # Get integrations for the user and their teams
        integrations = crud.integration.get_integrations(
            db=db, owner_id=current_user.id
        )

    # If no integrations found, return an empty list
    if not integrations:
        return []

    integration_ids = [integration.id for integration in integrations]

    # Use CRUD operation instead of direct query
    integration_history = crud.integration_history.get_integration_history(
        db=db, integration_ids=integration_ids, skip=skip, limit=limit
    )

    return integration_history


@router.get(
    "/",
    response_model=List[schemas.integration.Integration],
    dependencies=[jwt_auth],
)
def read_integrations(
    skip: int = 0,
    limit: int = 100,
    team_id: Optional[int] = Query(None, description="Filter by team ID"),
    db: Session = Depends(get_db),
    current_user: User = jwt_auth,
) -> Any:
    """
    Retrieve integrations.

    If team_id is provided, will show integrations owned by that team.
    Otherwise, shows integrations owned by the current user and all teams the user belongs to.
    """
    if current_user.is_superuser:
        # Superusers can see all integrations
        return crud.integration.get_integrations(db, skip=skip, limit=limit)

    if team_id:
        # Check if user is a member of the team
        check_team_membership(db, current_user, team_id)

        # Get integrations belonging to the specified team
        return crud.integration.get_integrations(
            db, skip=skip, limit=limit, team_id=team_id
        )
    else:
        # Get integrations for the user and their teams
        return crud.integration.get_integrations(
            db, skip=skip, limit=limit, owner_id=current_user.id
        )


@router.post(
    "/", response_model=schemas.integration.Integration, dependencies=[jwt_auth]
)
def create_integration(
    *,
    db: Session = Depends(get_db),
    integration_in: schemas.integration.IntegrationCreate,
    team_id: Optional[int] = Query(
        None, description="Team to assign the integration to"
    ),
    current_user: User = jwt_auth
) -> Any:
    """
    Create new integration.

    If team_id is provided, integration will be owned by the team.
    Otherwise, integration will be owned by the current user.
    """
    integration = crud.integration.get_integration_by_name(db, name=integration_in.name)
    if integration:
        raise HTTPException(
            status_code=400, detail="Integration with this name already exists."
        )

    if team_id:
        # Check if user is a member of the team
        check_team_membership(db, current_user, team_id)

        # Create integration owned by the team
        return crud.integration.create_integration(
            db=db,
            integration=integration_in,
            team_id=team_id,
            owner_type=OwnerType.TEAM,
        )
    else:
        # Create integration owned by the user
        return crud.integration.create_integration(
            db=db,
            integration=integration_in,
            owner_id=current_user.id,
            owner_type=OwnerType.USER,
        )


@router.get(
    "/{integration_id}",
    response_model=schemas.integration.Integration,
    dependencies=[jwt_auth],
)
def read_integration(
    *, db: Session = Depends(get_db), integration_id: int, current_user: User = jwt_auth
) -> Any:
    """
    Get integration by ID.
    """
    integration = crud.integration.get_integration(db=db, integration_id=integration_id)

    # Check permissions - will raise HTTPException if not allowed
    check_resource_permissions(db, current_user, integration, "access")

    return integration


@router.put(
    "/{integration_id}",
    response_model=schemas.integration.Integration,
    dependencies=[jwt_auth],
)
def update_integration(
    *,
    db: Session = Depends(get_db),
    integration_id: int,
    integration_in: schemas.integration.IntegrationUpdate,
    team_id: Optional[int] = Query(
        None, description="Transfer integration to this team"
    ),
    current_user: User = jwt_auth
) -> Any:
    """
    Update an integration.

    If team_id is provided, integration ownership will be transferred to the team.
    """
    integration = crud.integration.get_integration(db=db, integration_id=integration_id)

    # Check permissions - will raise HTTPException if not allowed
    check_resource_permissions(db, current_user, integration, "update")

    # Handle ownership transfer if team_id is provided
    if team_id:
        # Check if user is a member of the target team
        check_team_membership(db, current_user, team_id)

        integration.owner_id = team_id
        integration.owner_type = OwnerType.TEAM

    return crud.integration.update_integration(
        db=db, db_integration=integration, integration=integration_in
    )


@router.delete(
    "/{integration_id}",
    response_model=schemas.integration.Integration,
    dependencies=[jwt_auth],
)
def delete_integration(
    *, db: Session = Depends(get_db), integration_id: int, current_user: User = jwt_auth
) -> Any:
    """
    Delete an integration.
    """
    integration = crud.integration.get_integration(db=db, integration_id=integration_id)

    # Check permissions - will raise HTTPException if not allowed
    check_resource_permissions(db, current_user, integration, "delete")

    return crud.integration.delete_integration(db=db, db_integration=integration)


@router.get(
    "/history",
    response_model=List[schemas.integration_history.IntegrationHistory],
    dependencies=[jwt_auth],
)
def read_all_integration_history(
    *,
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    team_id: Optional[int] = Query(None, description="Filter by team ID"),
    current_user: User = jwt_auth
) -> Any:
    """
    Get history for all integrations.

    If team_id is provided, returns history for integrations owned by that team.
    Otherwise, returns history for integrations owned by the current user and their teams.
    Returns an empty array if no history is found.
    """
    if current_user.is_superuser:
        # Get all integrations if superuser
        integrations = crud.integration.get_integrations(db=db)
    elif team_id:
        # Check if user is a member of the team
        check_team_membership(db, current_user, team_id)

        # Get integrations belonging to the specified team
        integrations = crud.integration.get_integrations(db=db, team_id=team_id)
    else:
        # Get integrations for the user and their teams
        integrations = crud.integration.get_integrations(
            db=db, owner_id=current_user.id
        )

    # If no integrations found, return an empty list
    if not integrations:
        return []

    integration_ids = [integration.id for integration in integrations]

    # Use CRUD operation instead of direct query
    integration_history = crud.integration_history.get_integration_history(
        db=db, integration_ids=integration_ids, skip=skip, limit=limit
    )

    return integration_history


@router.get(
    "/{integration_id}/history",
    response_model=List[schemas.integration_history.IntegrationHistory],
    dependencies=[jwt_auth],
)
def read_integration_history(
    *,
    db: Session = Depends(get_db),
    integration_id: int,
    flowId: int = None,
    skip: int = 0,
    limit: int = 100,
    current_user: User = jwt_auth
) -> Any:
    """
    Get history for a specific integration.
    Returns an empty array if no history is found.
    """
    integration = crud.integration.get_integration(db=db, integration_id=integration_id)

    # Check permissions - will raise HTTPException if not allowed
    check_resource_permissions(db, current_user, integration, "access")

    # Use CRUD operation instead of direct query
    integration_history = crud.integration_history.get_integration_history(
        db=db, integration_id=integration_id, skip=skip, limit=limit, flowId=flowId
    )

    return integration_history


@router.get(
    "/{integration_id}/history/{history_id}",
    response_model=schemas.integration_history.IntegrationHistory,
    dependencies=[jwt_auth],
)
def read_integration_history_by_id(
    *,
    db: Session = Depends(get_db),
    integration_id: int,
    history_id: int,
    current_user: User = jwt_auth
) -> Any:
    """
    Get a specific integration history entry by ID.
    """
    # First verify the integration exists and user has access to it
    integration = crud.integration.get_integration(db=db, integration_id=integration_id)

    # Check permissions - will raise HTTPException if not allowed
    check_resource_permissions(db, current_user, integration, "access")

    # Get the specific history entry
    history_entry = crud.integration_history.get_integration_history_by_id(
        db=db, history_id=history_id
    )

    if not history_entry:
        raise HTTPException(
            status_code=404, detail="Integration history entry not found"
        )

    # Verify the history entry belongs to the requested integration
    if history_entry.integration_id != integration_id:
        raise HTTPException(
            status_code=404,
            detail="Integration history entry not found for this integration",
        )

    return history_entry
