from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app import crud, schemas
from app.core.auth import jwt_auth, check_resource_permissions, check_team_membership
from app.db.database import get_db
from app.models.user import User
from app.models.flow import Flow
from app.models.flow_history import FlowHistory
from app.models.enums import OwnerType
from app.crud import team as crud_team

router = APIRouter()


@router.get(
    "/all-history",
    response_model=List[schemas.flow_history.FlowHistory],
    dependencies=[jwt_auth],
)
def read_all_flow_history(
    *,
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    team_id: Optional[int] = Query(None, description="Filter by team ID"),
    current_user: User = jwt_auth
) -> Any:
    """
    Get history for all flows.
    If team_id is provided, returns history for flows owned by that team.
    Otherwise, returns history for flows owned by the current user and their teams.
    Returns an empty array if no history is found.
    """
    if current_user.is_superuser:
        # Get all flows if superuser
        flows = crud.flow.get_flows(db=db)
    elif team_id:
        # Check if user is a member of the team
        check_team_membership(db, current_user, team_id)

        # Get flows belonging to the specified team
        flows = crud.flow.get_flows(db=db, team_id=team_id)
    else:
        # Get flows for the user and their teams
        flows = crud.flow.get_flows(db=db, owner_id=current_user.id)

    # If no flows found, return an empty list
    if not flows:
        return []

    flow_ids = [flow.id for flow in flows]

    # Use CRUD operation instead of direct query
    flow_history = crud.flow_history.get_flow_history(
        db=db, flow_ids=flow_ids, skip=skip, limit=limit
    )

    return flow_history


@router.get("/", response_model=List[schemas.flow.Flow], dependencies=[jwt_auth])
def read_flows(
    skip: int = 0,
    limit: int = 100,
    team_id: Optional[int] = Query(None, description="Filter by team ID"),
    db: Session = Depends(get_db),
    current_user: User = jwt_auth,
) -> Any:
    """
    Retrieve flows.

    If team_id is provided, will show flows owned by that team.
    Otherwise, shows flows owned by the current user and all teams the user belongs to.
    """
    if current_user.is_superuser:
        # Superusers can see all flows
        return crud.flow.get_flows(db, skip=skip, limit=limit)

    if team_id:
        # Check if user is a member of the team
        check_team_membership(db, current_user, team_id)

        # Get flows belonging to the specified team
        return crud.flow.get_flows(db, skip=skip, limit=limit, team_id=team_id)
    else:
        # Get flows for the user and their teams
        return crud.flow.get_flows(db, skip=skip, limit=limit, owner_id=current_user.id)


@router.post("/", response_model=schemas.flow.Flow, dependencies=[jwt_auth])
def create_flow(
    *,
    db: Session = Depends(get_db),
    flow_in: schemas.flow.FlowCreate,
    team_id: Optional[int] = Query(None, description="Team to assign the flow to"),
    current_user: User = jwt_auth
) -> Any:
    """
    Create new flow.

    If team_id is provided, flow will be owned by the team.
    Otherwise, flow will be owned by the current user.
    """
    flow = crud.flow.get_flow_by_name(db, name=flow_in.name)
    if flow:
        raise HTTPException(
            status_code=400, detail="Flow with this name already exists."
        )

    if team_id:
        # Check if user is a member of the team
        check_team_membership(db, current_user, team_id)

        # Create flow owned by the team
        return crud.flow.create_flow(
            db=db, flow=flow_in, team_id=team_id, owner_type=OwnerType.TEAM
        )
    else:
        # Create flow owned by the user
        return crud.flow.create_flow(
            db=db, flow=flow_in, owner_id=current_user.id, owner_type=OwnerType.USER
        )


@router.get("/{flow_id}", response_model=schemas.flow.Flow, dependencies=[jwt_auth])
def read_flow(
    *, db: Session = Depends(get_db), flow_id: int, current_user: User = jwt_auth
) -> Any:
    """
    Get flow by ID.
    """
    flow = crud.flow.get_flow(db=db, flow_id=flow_id)

    # Check permissions - will raise HTTPException if not allowed
    check_resource_permissions(db, current_user, flow, "access")

    return flow


@router.put("/{flow_id}", response_model=schemas.flow.Flow, dependencies=[jwt_auth])
def update_flow(
    *,
    db: Session = Depends(get_db),
    flow_id: int,
    flow_in: schemas.flow.FlowUpdate,
    team_id: Optional[int] = Query(None, description="Transfer flow to this team"),
    current_user: User = jwt_auth
) -> Any:
    """
    Update a flow.

    If team_id is provided, flow ownership will be transferred to the team.
    """
    flow = crud.flow.get_flow(db=db, flow_id=flow_id)

    # Check permissions - will raise HTTPException if not allowed
    check_resource_permissions(db, current_user, flow, "update")

    # Handle ownership transfer if team_id is provided
    if team_id:
        # Check if user is a member of the target team
        check_team_membership(db, current_user, team_id)

        flow.owner_id = team_id
        flow.owner_type = OwnerType.TEAM

    return crud.flow.update_flow(db=db, db_flow=flow, flow=flow_in)


@router.delete("/{flow_id}", response_model=schemas.flow.Flow, dependencies=[jwt_auth])
def delete_flow(
    *, db: Session = Depends(get_db), flow_id: int, current_user: User = jwt_auth
) -> Any:
    """
    Delete a flow.
    """
    flow = crud.flow.get_flow(db=db, flow_id=flow_id)

    # Check permissions - will raise HTTPException if not allowed
    check_resource_permissions(db, current_user, flow, "delete")

    return crud.flow.delete_flow(db=db, db_flow=flow)


@router.get(
    "/{flow_id}/history",
    response_model=List[schemas.flow_history.FlowHistory],
    dependencies=[jwt_auth],
)
def read_flow_history(
    *,
    db: Session = Depends(get_db),
    flow_id: int,
    skip: int = 0,
    limit: int = 100,
    current_user: User = jwt_auth
) -> Any:
    """
    Get history for a specific flow.
    Returns an empty array if no history is found.
    """
    flow = crud.flow.get_flow(db=db, flow_id=flow_id)

    # Check permissions - will raise HTTPException if not allowed
    check_resource_permissions(db, current_user, flow, "access")

    # Use CRUD operation instead of direct query
    flow_history = crud.flow_history.get_flow_history(
        db=db, flow_id=flow_id, skip=skip, limit=limit
    )

    return flow_history


@router.get(
    "/{flow_id}/history/{history_id}",
    response_model=schemas.flow_history.FlowHistory,
    dependencies=[jwt_auth],
)
def read_flow_history_by_id(
    *,
    db: Session = Depends(get_db),
    flow_id: int,
    history_id: int,
    current_user: User = jwt_auth
) -> Any:
    """
    Get a specific flow history entry by ID.
    """
    # First verify the flow exists and user has access to it
    flow = crud.flow.get_flow(db=db, flow_id=flow_id)

    # Check permissions - will raise HTTPException if not allowed
    check_resource_permissions(db, current_user, flow, "access")

    # Get the specific history entry
    history_entry = crud.flow_history.get_flow_history_by_id(
        db=db, history_id=history_id
    )

    if not history_entry:
        raise HTTPException(status_code=404, detail="Flow history entry not found")

    # Verify the history entry belongs to the requested flow
    if history_entry.flow_id != flow_id:
        raise HTTPException(
            status_code=404, detail="Flow history entry not found for this flow"
        )

    return history_entry
