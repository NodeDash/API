from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app import crud, schemas
from app.core.auth import jwt_auth, check_resource_permissions, check_team_membership
from app.db.database import get_db
from app.models.user import User
from app.models.label import Label
from app.models.label_history import LabelHistory
from app.models.enums import OwnerType
from app.crud import team as crud_team

router = APIRouter()


@router.get(
    "/all-history",
    response_model=List[schemas.label_history.LabelHistory],
    dependencies=[jwt_auth],
)
def read_all_label_history(
    *,
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    flow_id: int = None,
    team_id: Optional[int] = Query(None, description="Filter by team ID"),
    current_user: User = jwt_auth,
) -> Any:
    """
    Get history for all labels.

    If team_id is provided, returns history for labels owned by that team.
    Otherwise, returns history for labels owned by the current user and their teams.
    Can be filtered by flow_id.
    Returns an empty array if no history is found.

    Parameters:
        flow_id: Optional flow ID to filter by
        team_id: Optional team ID to filter by
    """
    if current_user.is_superuser:
        # Get all labels if superuser
        labels = crud.label.get_labels(db=db)
    elif team_id:
        # Check if user is a member of the team
        check_team_membership(db, current_user, team_id)

        # Get labels belonging to the specified team
        labels = crud.label.get_labels(db=db, team_id=team_id)
    else:
        # Get labels for the user and their teams
        labels = crud.label.get_labels(db=db, owner_id=current_user.id)

    # If no labels found, return an empty list
    if not labels:
        return []

    label_ids = [label.id for label in labels]

    # Use CRUD operation instead of direct query
    label_history = crud.label_history.get_label_history(
        db=db,
        label_ids=label_ids,
        flow_id=flow_id,
        skip=skip,
        limit=limit,
    )

    return label_history


@router.get("/", response_model=List[schemas.label.Label], dependencies=[jwt_auth])
def read_labels(
    skip: int = 0,
    limit: int = 100,
    team_id: Optional[int] = Query(None, description="Filter by team ID"),
    db: Session = Depends(get_db),
    current_user: User = jwt_auth,
) -> Any:
    """
    Retrieve labels.

    If team_id is provided, will show labels owned by that team.
    Otherwise, shows labels owned by the current user and all teams the user belongs to.
    """
    if current_user.is_superuser:
        # Superusers can see all labels
        return crud.label.get_labels(db, skip=skip, limit=limit)

    if team_id:
        # Check if user is a member of the team
        check_team_membership(db, current_user, team_id)

        # Get labels belonging to the specified team
        return crud.label.get_labels(db, skip=skip, limit=limit, team_id=team_id)
    else:
        # Get labels for the user and their teams
        return crud.label.get_labels(
            db, skip=skip, limit=limit, owner_id=current_user.id
        )


@router.post("/", response_model=schemas.label.Label, dependencies=[jwt_auth])
def create_label(
    *,
    db: Session = Depends(get_db),
    label_in: schemas.label.LabelCreate,
    team_id: Optional[int] = Query(None, description="Team to assign the label to"),
    current_user: User = jwt_auth,
) -> Any:
    """
    Create new label.

    If team_id is provided, label will be owned by the team.
    Otherwise, label will be owned by the current user.
    """
    label = crud.label.get_label_by_name(db, name=label_in.name)
    if label:
        raise HTTPException(
            status_code=400, detail="Label with this name already exists."
        )

    if team_id:
        # Check if user is a member of the team
        check_team_membership(db, current_user, team_id)

        print(
            f"Creating label: {label_in}, team_id: {team_id}, device_ids: {label_in.device_ids}"
        )
        # Create label owned by the team
        return crud.label.create_label(
            db=db, label=label_in, team_id=team_id, owner_type=OwnerType.TEAM
        )
    else:
        print(
            f"Creating label: {label_in}, owner_id: {current_user.id}, device_ids: {label_in.device_ids}"
        )
        # Create label owned by the user
        return crud.label.create_label(
            db=db, label=label_in, owner_id=current_user.id, owner_type=OwnerType.USER
        )


@router.get("/{label_id}", response_model=schemas.label.Label, dependencies=[jwt_auth])
def read_label(
    *, db: Session = Depends(get_db), label_id: int, current_user: User = jwt_auth
) -> Any:
    """
    Get label by ID.
    """
    label = crud.label.get_label(db=db, label_id=label_id)

    # Check permissions - will raise HTTPException if not allowed
    check_resource_permissions(db, current_user, label, "access")

    return label


@router.put("/{label_id}", response_model=schemas.label.Label, dependencies=[jwt_auth])
def update_label(
    *,
    db: Session = Depends(get_db),
    label_id: int,
    label_in: schemas.label.LabelUpdate,
    team_id: Optional[int] = Query(None, description="Transfer label to this team"),
    current_user: User = jwt_auth,
) -> Any:
    """
    Update a label.

    If team_id is provided, label ownership will be transferred to the team.
    """
    label = crud.label.get_label(db=db, label_id=label_id)

    # Check permissions - will raise HTTPException if not allowed
    check_resource_permissions(db, current_user, label, "update")

    # Handle ownership transfer if team_id is provided
    if team_id:
        # Check if user is a member of the target team
        check_team_membership(db, current_user, team_id)

        label.owner_id = team_id
        label.owner_type = OwnerType.TEAM

    return crud.label.update_label(db=db, db_label=label, label=label_in)


@router.delete(
    "/{label_id}", response_model=schemas.label.Label, dependencies=[jwt_auth]
)
def delete_label(
    *, db: Session = Depends(get_db), label_id: int, current_user: User = jwt_auth
) -> Any:
    """
    Delete a label.
    """
    label = crud.label.get_label(db=db, label_id=label_id)

    # Check permissions - will raise HTTPException if not allowed
    check_resource_permissions(db, current_user, label, "delete")

    return crud.label.delete_label(db=db, db_label=label)


@router.post(
    "/{label_id}/devices/{device_id}",
    response_model=schemas.label.Label,
    dependencies=[jwt_auth],
)
def add_device_to_label(
    *,
    db: Session = Depends(get_db),
    label_id: int,
    device_id: int,
    current_user: User = jwt_auth,
) -> Any:
    """
    Add device to a label.
    """
    label = crud.label.get_label(db=db, label_id=label_id)

    # Check permissions for label - will raise HTTPException if not allowed
    check_resource_permissions(db, current_user, label, "update")

    # Check if the user has access to the device they want to add
    device = crud.device.get_device(db=db, device_id=device_id)

    # Check permissions for device - will raise HTTPException if not allowed
    check_resource_permissions(db, current_user, device, "access")

    return crud.label.add_device_to_label(db=db, db_label=label, device_id=device_id)


@router.delete(
    "/{label_id}/devices/{device_id}",
    response_model=schemas.label.Label,
    dependencies=[jwt_auth],
)
def remove_device_from_label(
    *,
    db: Session = Depends(get_db),
    label_id: int,
    device_id: int,
    current_user: User = jwt_auth,
) -> Any:
    """
    Remove device from a label.
    """
    label = crud.label.get_label(db=db, label_id=label_id)

    # Check permissions - will raise HTTPException if not allowed
    check_resource_permissions(db, current_user, label, "update")

    return crud.label.remove_device_from_label(
        db=db, db_label=label, device_id=device_id
    )


@router.get(
    "/{label_id}/devices",
    response_model=List[schemas.device.Device],
    dependencies=[jwt_auth],
)
def read_label_devices(
    *, db: Session = Depends(get_db), label_id: int, current_user: User = jwt_auth
) -> Any:
    """
    Get all devices assigned to a specific label.
    """
    label = crud.label.get_label(db=db, label_id=label_id)

    # Check permissions - will raise HTTPException if not allowed
    check_resource_permissions(db, current_user, label, "access")

    # Return devices associated with this label that the user has access to
    accessible_devices = []
    for device in label.devices:
        # For superusers, include all devices
        if current_user.is_superuser:
            accessible_devices.append(device)
        # For regular users, include devices they own or from teams they are members of
        elif device.owner_type == OwnerType.USER and device.owner_id == current_user.id:
            accessible_devices.append(device)
        elif device.owner_type == OwnerType.TEAM:
            if crud_team.is_user_in_team(db, device.owner_id, current_user.id):
                accessible_devices.append(device)

    return accessible_devices


@router.get(
    "/{label_id}/history",
    response_model=List[schemas.label_history.LabelHistory],
    dependencies=[jwt_auth],
)
def read_label_history(
    *,
    db: Session = Depends(get_db),
    label_id: int,
    flowId: int = None,
    skip: int = 0,
    limit: int = 100,
    current_user: User = jwt_auth,
) -> Any:
    """
    Get history for a specific label. Can be filtered by flow_id.
    Returns an empty array if no history is found.

    Parameters:
        flow_id: Optional flow ID to filter by
    """
    label = crud.label.get_label(db=db, label_id=label_id)

    # Check permissions - will raise HTTPException if not allowed
    check_resource_permissions(db, current_user, label, "access")

    # Use CRUD operation instead of direct query
    label_history = crud.label_history.get_label_history(
        db=db,
        label_id=label_id,
        flow_id=flowId,
        skip=skip,
        limit=limit,
    )

    return label_history


@router.get(
    "/{label_id}/history/{history_id}",
    response_model=schemas.label_history.LabelHistory,
    dependencies=[jwt_auth],
)
def read_label_history_by_id(
    *,
    db: Session = Depends(get_db),
    label_id: int,
    history_id: int,
    current_user: User = jwt_auth,
) -> Any:
    """
    Get a specific label history entry by ID.
    """
    # First verify the label exists and user has access to it
    label = crud.label.get_label(db=db, label_id=label_id)

    # Check permissions - will raise HTTPException if not allowed
    check_resource_permissions(db, current_user, label, "access")

    # Get the specific history entry
    history_entry = crud.label_history.get_label_history_by_id(
        db=db, history_id=history_id
    )

    if not history_entry:
        raise HTTPException(status_code=404, detail="Label history entry not found")

    # Verify the history entry belongs to the requested label
    if history_entry.label_id != label_id:
        raise HTTPException(
            status_code=404, detail="Label history entry not found for this label"
        )

    return history_entry
