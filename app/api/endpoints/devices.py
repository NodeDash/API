from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Body, Query
from sqlalchemy.orm import Session

from app import crud, schemas
from app.core.auth import jwt_auth, check_resource_permissions, check_team_membership
from app.db.database import get_db
from app.models.user import User
from app.models.enums import OwnerType
from app.crud import team as crud_team

router = APIRouter()


@router.get(
    "/history",
    response_model=List[schemas.device_history.DeviceHistory],
    dependencies=[jwt_auth],
)
def read_all_device_history(
    *,
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    team_id: Optional[int] = Query(None, description="Filter by team ID"),
    current_user: User = jwt_auth
) -> Any:
    """
    Retrieve historical data for all devices accessible to the user.

    This endpoint returns a chronological list of device states and events,
    useful for tracking device status changes over time.

    Parameters:
    - **db**: Database session dependency
    - **skip**: Number of records to skip for pagination
    - **limit**: Maximum number of records to return
    - **team_id**: Optional filter to show only devices belonging to a specific team
    - **current_user**: Authenticated user from JWT token

    Returns:
    - List of DeviceHistory objects containing timestamp, device ID, status and other details

    Access Control:
    - Users can only see history for their own devices or devices belonging to their teams
    - Returns an empty array if no history is found
    """
    if team_id:
        # Check if user is a member of the team
        check_team_membership(db, current_user, team_id)

        # Query device history entries for devices owned by the specified team
        devices = crud.device.get_devices(db=db, team_id=team_id)
    else:
        # Query device history entries for all devices owned by the current user
        devices = crud.device.get_devices(db=db, owner_id=current_user.id)

    # If no devices found, return an empty list
    if not devices:
        return []

    device_ids = [device.id for device in devices]

    # Use the CRUD operation instead of direct query
    device_history = crud.device_history.get_device_history(
        db=db, device_ids=device_ids, skip=skip, limit=limit
    )

    return device_history


@router.get("/", response_model=List[schemas.device.Device])
def read_devices(
    skip: int = 0,
    limit: int = 100,
    team_id: Optional[int] = Query(None, description="Filter by team ID"),
    db: Session = Depends(get_db),
    current_user: User = jwt_auth,
):
    """
    Retrieve a list of all devices accessible to the user.

    This endpoint returns devices with their current status and configuration details.
    Results can be paginated using skip and limit parameters.

    Parameters:
    - **skip**: Number of records to skip for pagination
    - **limit**: Maximum number of records to return
    - **team_id**: Optional filter to show only devices belonging to a specific team
    - **db**: Database session dependency
    - **current_user**: Authenticated user from JWT token

    Returns:
    - List of Device objects with their complete details

    Access Control:
    - Users can only see their own devices or devices belonging to their teams
    - Superusers can see all devices when not filtering by team
    """
    """
    Retrieve devices.

    If team_id is provided, will show devices owned by that team.
    Otherwise, shows devices owned by the current user and all teams the user belongs to.
    """
    if current_user.is_superuser:
        # Superusers can see all devices
        return crud.device.get_devices(db, skip=skip, limit=limit)

    if team_id:
        # Check if user is a member of the team
        check_team_membership(db, current_user, team_id)

        # Get devices belonging to the specified team
        return crud.device.get_devices(db, skip=skip, limit=limit, team_id=team_id)
    else:
        # Get devices for the user and their teams
        return crud.device.get_devices(
            db, skip=skip, limit=limit, owner_id=current_user.id
        )


@router.post("/", response_model=schemas.device.Device)
def create_device(
    device: schemas.device.DeviceCreate,
    team_id: Optional[int] = Query(None, description="Team to assign the device to"),
    db: Session = Depends(get_db),
    current_user: User = jwt_auth,
):
    """
    Create a new device in the system.

    This endpoint registers a new device with the provided configuration details.
    The device will be owned either by the current user or by a specified team.

    Parameters:
    - **device**: Device creation data including required fields like name, dev_eui, etc.
    - **team_id**: Optional team ID to assign ownership to a team instead of the current user
    - **db**: Database session dependency
    - **current_user**: Authenticated user from JWT token

    Returns:
    - Complete Device object with generated ID and default values

    Access Control:
    - Users can create devices for themselves
    - Users can create devices for teams they belong to
    - Superusers can create devices for any team
    """
    """
    Create new device.

    If team_id is provided, device will be owned by the team.
    Otherwise, device will be owned by the current user.
    """
    # Check if a device with the same DEV EUI exists
    db_device = crud.device.get_device_by_dev_eui(db, dev_eui=device.dev_eui)
    if db_device:
        raise HTTPException(
            status_code=400, detail="Device with this DEV EUI already exists"
        )

    if team_id:
        # Check if user is a member of the team
        check_team_membership(db, current_user, team_id)

        # Create device owned by the team
        return crud.device.create_device(
            db=db, device=device, team_id=team_id, owner_type=OwnerType.TEAM
        )
    else:
        # Create device owned by the user
        return crud.device.create_device(
            db=db, device=device, owner_id=current_user.id, owner_type=OwnerType.USER
        )


@router.get("/{device_id}", response_model=schemas.device.Device)
def read_device(
    device_id: int,
    db: Session = Depends(get_db),
    current_user: User = jwt_auth,
):
    """
    Retrieve a specific device by its ID.

    This endpoint returns detailed information about a single device
    including its current status, configuration, and ownership details.

    Parameters:
    - **device_id**: Unique identifier of the device to retrieve
    - **db**: Database session dependency
    - **current_user**: Authenticated user from JWT token

    Returns:
    - Complete Device object with all its attributes

    Access Control:
    - Users can only retrieve devices they own
    - Users can retrieve devices belonging to teams they are members of
    - Superusers can retrieve any device

    Raises:
    - 404: If the device doesn't exist
    - 403: If the user doesn't have access to the device
    """
    """
    Get device by ID.
    """
    device = crud.device.get_device(db, device_id=device_id)

    # Check permissions - will raise HTTPException if not allowed
    check_resource_permissions(db, current_user, device, "access")

    return device


@router.put("/{device_id}", response_model=schemas.device.Device)
def update_device(
    device_id: int,
    device: schemas.device.DeviceUpdate,
    team_id: Optional[int] = Query(None, description="Transfer device to this team"),
    db: Session = Depends(get_db),
    current_user: User = jwt_auth,
):
    """
    Update a device's details by ID.

    This endpoint allows modification of device properties and optionally
    transferring device ownership to a team.

    Parameters:
    - **device_id**: Unique identifier of the device to update
    - **device**: Updated device data
    - **team_id**: Optional team ID to transfer device ownership
    - **db**: Database session dependency
    - **current_user**: Authenticated user from JWT token

    Returns:
    - Updated Device object with all attributes

    Access Control:
    - Users can only update devices they own
    - Users can update devices belonging to teams they are members of
    - Superusers can update any device
    - Ownership can only be transferred to teams the user belongs to

    Raises:
    - 404: If the device doesn't exist
    - 403: If the user doesn't have access to the device
    """
    """
    Update device.

    If team_id is provided, device ownership will be transferred to the team.
    """
    db_device = crud.device.get_device(db, device_id=device_id)

    # Check permissions - will raise HTTPException if not allowed
    check_resource_permissions(db, current_user, db_device, "update")

    # Handle ownership transfer if team_id is provided
    if team_id:
        # Check if user is a member of the target team
        check_team_membership(db, current_user, team_id, raise_exception=True)

        db_device.owner_id = team_id
        db_device.owner_type = OwnerType.TEAM

    return crud.device.update_device(db=db, db_device=db_device, device=device)


@router.delete("/{device_id}", response_model=schemas.device.Device)
def delete_device(
    device_id: int,
    db: Session = Depends(get_db),
    current_user: User = jwt_auth,
):
    """
    Delete a device by ID.

    This endpoint permanently removes a device from the system.
    Related historical data may be retained based on system configuration.

    Parameters:
    - **device_id**: Unique identifier of the device to delete
    - **db**: Database session dependency
    - **current_user**: Authenticated user from JWT token

    Returns:
    - The deleted Device object

    Access Control:
    - Users can only delete devices they own
    - Users can delete devices belonging to teams they are members of
    - Superusers can delete any device

    Raises:
    - 404: If the device doesn't exist
    - 403: If the user doesn't have access to the device
    """
    """
    Delete device.
    """
    db_device = crud.device.get_device(db, device_id=device_id)

    # Check permissions - will raise HTTPException if not allowed
    check_resource_permissions(db, current_user, db_device, "delete")

    return crud.device.delete_device(db=db, db_device=db_device)


@router.get(
    "/{device_id}/history",
    response_model=List[schemas.device_history.DeviceHistory],
    dependencies=[jwt_auth],
)
def read_device_history(
    *,
    db: Session = Depends(get_db),
    device_id: int,
    flowId: int = None,
    skip: int = 0,
    limit: int = 100,
    current_user: User = jwt_auth
) -> Any:
    """
    Retrieve historical data for a specific device.

    This endpoint returns a chronological list of a device's states and events,
    useful for tracking its status changes over time.

    Parameters:
    - **db**: Database session dependency
    - **device_id**: Unique identifier of the device to get history for
    - **flowId**: Optional filter to show only events related to a specific flow
    - **skip**: Number of records to skip for pagination
    - **limit**: Maximum number of records to return
    - **current_user**: Authenticated user from JWT token

    Returns:
    - List of DeviceHistory objects containing timestamp, status and other details

    Access Control:
    - Users can only see history for devices they own
    - Users can see history for devices belonging to teams they are members of
    - Superusers can see history for any device

    Raises:
    - 404: If the device doesn't exist
    - 403: If the user doesn't have access to the device
    """
    """
    Get history for a specific device.
    Returns an empty array if no history is found.
    """
    device = crud.device.get_device(db=db, device_id=device_id)

    # Check permissions - will raise HTTPException if not allowed
    check_resource_permissions(db, current_user, device, "access")

    # Use CRUD operation instead of direct query
    device_history = crud.device_history.get_device_history(
        db=db, device_id=device_id, skip=skip, limit=limit, flowId=flowId
    )

    return device_history


@router.get(
    "/{device_id}/labels",
    response_model=List[schemas.label.Label],
    dependencies=[jwt_auth],
)
def read_device_labels(
    *, db: Session = Depends(get_db), device_id: int, current_user: User = jwt_auth
) -> Any:
    """
    Retrieve all labels associated with a specific device.

    This endpoint returns all labels that have been assigned to the device,
    which can be used for grouping, filtering, and organization purposes.

    Parameters:
    - **db**: Database session dependency
    - **device_id**: Unique identifier of the device to get labels for
    - **current_user**: Authenticated user from JWT token

    Returns:
    - List of Label objects assigned to this device

    Access Control:
    - Users can only see labels for devices they own
    - Users can see labels for devices belonging to teams they are members of
    - Superusers can see labels for any device

    Raises:
    - 404: If the device doesn't exist
    - 403: If the user doesn't have access to the device
    """
    """
    Get all labels assigned to a specific device.
    """
    device = crud.device.get_device(db=db, device_id=device_id)

    # Check permissions - will raise HTTPException if not allowed
    check_resource_permissions(db, current_user, device, "access")

    # Return the labels associated with this device
    return device.labels
