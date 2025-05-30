from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app import crud, schemas
from app.core.auth import jwt_auth, check_resource_permissions, check_team_membership
from app.db.database import get_db
from app.models.user import User
from app.models.function import Function
from app.models.function_history import FunctionHistory
from app.models.enums import OwnerType
from app.crud import team as crud_team

router = APIRouter()


@router.get(
    "/", response_model=List[schemas.function.Function], dependencies=[jwt_auth]
)
def read_functions(
    skip: int = 0,
    limit: int = 100,
    team_id: Optional[int] = Query(None, description="Filter by team ID"),
    db: Session = Depends(get_db),
    current_user: User = jwt_auth,
) -> Any:
    """
    Retrieve functions.

    If team_id is provided, will show functions owned by that team.
    Otherwise, shows functions owned by the current user and all teams the user belongs to.
    """
    if current_user.is_superuser:
        # Superusers can see all functions
        return crud.function.get_functions(db, skip=skip, limit=limit)

    if team_id:
        # Check if user is a member of the team
        check_team_membership(db, current_user, team_id)

        # Get functions belonging to the specified team
        return crud.function.get_functions(db, skip=skip, limit=limit, team_id=team_id)
    else:
        # Get functions for the user and their teams
        return crud.function.get_functions(
            db, skip=skip, limit=limit, owner_id=current_user.id
        )


@router.post("/", response_model=schemas.function.Function, dependencies=[jwt_auth])
def create_function(
    *,
    db: Session = Depends(get_db),
    function_in: schemas.function.FunctionCreate,
    team_id: Optional[int] = Query(None, description="Team to assign the function to"),
    current_user: User = jwt_auth
) -> Any:
    """
    Create new function.

    If team_id is provided, function will be owned by the team.
    Otherwise, function will be owned by the current user.
    """
    function = crud.function.get_function_by_name(db, name=function_in.name)
    if function:
        raise HTTPException(
            status_code=400, detail="Function with this name already exists."
        )

    if team_id:
        # Check if user is a member of the team
        check_team_membership(db, current_user, team_id)

        # Create function owned by the team
        return crud.function.create_function(
            db=db, function=function_in, team_id=team_id, owner_type=OwnerType.TEAM
        )
    else:
        # Create function owned by the user
        return crud.function.create_function(
            db=db,
            function=function_in,
            owner_id=current_user.id,
            owner_type=OwnerType.USER,
        )


# Get all function history for a user - moved before /{function_id} patterns
@router.get(
    "/all-history",
    response_model=List[schemas.function_history.FunctionHistory],
    dependencies=[jwt_auth],
)
def read_user_function_history(
    *,
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    team_id: Optional[int] = Query(None, description="Filter by team ID"),
    current_user: User = jwt_auth
) -> Any:
    """
    Get all function history entries.

    If team_id is provided, returns history for functions owned by that team.
    Otherwise, returns history for functions owned by the current user and their teams.
    """
    if current_user.is_superuser:
        # Get all functions if superuser
        functions = crud.function.get_functions(db=db)
    elif team_id:
        # Check if user is a member of the team
        check_team_membership(db, current_user, team_id)

        # Get functions belonging to the specified team
        functions = crud.function.get_functions(db=db, team_id=team_id)
    else:
        # Get functions for the user and their teams
        functions = crud.function.get_functions(db=db, owner_id=current_user.id)

    # If no functions found, return an empty list
    if not functions:
        return []

    function_ids = [function.id for function in functions]

    # Use CRUD operation instead of direct query
    function_history = crud.function_history.get_function_history(
        db=db, function_ids=function_ids, skip=skip, limit=limit
    )

    return function_history


@router.get(
    "/history",
    response_model=List[schemas.function_history.FunctionHistory],
    dependencies=[jwt_auth],
)
def read_all_function_history(
    *,
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    team_id: Optional[int] = Query(None, description="Filter by team ID"),
    current_user: User = jwt_auth
) -> Any:
    """
    Get history for all functions.

    If team_id is provided, returns history for functions owned by that team.
    Otherwise, returns history for functions owned by the current user and their teams.
    Returns an empty array if no history is found.
    """
    if current_user.is_superuser:
        # Get all functions if superuser
        functions = crud.function.get_functions(db=db)
    elif team_id:
        # Check if user is a member of the team
        check_team_membership(db, current_user, team_id)

        # Get functions belonging to the specified team
        functions = crud.function.get_functions(db=db, team_id=team_id)
    else:
        # Get functions for the user and their teams
        functions = crud.function.get_functions(db=db, owner_id=current_user.id)

    # If no functions found, return an empty list
    if not functions:
        return []

    function_ids = [function.id for function in functions]

    # Use CRUD operation instead of direct query
    function_history = crud.function_history.get_function_history(
        db=db, function_ids=function_ids, skip=skip, limit=limit
    )

    return function_history


@router.get(
    "/{function_id}", response_model=schemas.function.Function, dependencies=[jwt_auth]
)
def read_function(
    *, db: Session = Depends(get_db), function_id: int, current_user: User = jwt_auth
) -> Any:
    """
    Get function by ID.
    """
    function = crud.function.get_function(db=db, function_id=function_id)

    # Check permissions - will raise HTTPException if not allowed
    check_resource_permissions(db, current_user, function, "access")

    return function


@router.put(
    "/{function_id}", response_model=schemas.function.Function, dependencies=[jwt_auth]
)
def update_function(
    *,
    db: Session = Depends(get_db),
    function_id: int,
    function_in: schemas.function.FunctionUpdate,
    team_id: Optional[int] = Query(None, description="Transfer function to this team"),
    current_user: User = jwt_auth
) -> Any:
    """
    Update a function.

    If team_id is provided, function ownership will be transferred to the team.
    """
    function = crud.function.get_function(db=db, function_id=function_id)

    # Check permissions - will raise HTTPException if not allowed
    check_resource_permissions(db, current_user, function, "update")

    # Handle ownership transfer if team_id is provided
    if team_id:
        # Check if user is a member of the target team
        check_team_membership(db, current_user, team_id)

        function.owner_id = team_id
        function.owner_type = OwnerType.TEAM

    return crud.function.update_function(
        db=db, db_function=function, function=function_in
    )


@router.delete(
    "/{function_id}", response_model=schemas.function.Function, dependencies=[jwt_auth]
)
def delete_function(
    *, db: Session = Depends(get_db), function_id: int, current_user: User = jwt_auth
) -> Any:
    """
    Delete a function.
    """
    function = crud.function.get_function(db=db, function_id=function_id)

    # Check permissions - will raise HTTPException if not allowed
    check_resource_permissions(db, current_user, function, "delete")

    return crud.function.delete_function(db=db, db_function=function)


@router.get(
    "/{function_id}/history",
    response_model=List[schemas.function_history.FunctionHistory],
    dependencies=[jwt_auth],
)
def read_function_history(
    *,
    db: Session = Depends(get_db),
    function_id: int,
    flowId: int = None,
    skip: int = 0,
    limit: int = 100,
    current_user: User = jwt_auth
) -> Any:
    """
    Get history for a specific function.
    Returns an empty array if no history is found.
    """
    function = crud.function.get_function(db=db, function_id=function_id)

    # Check permissions - will raise HTTPException if not allowed
    check_resource_permissions(db, current_user, function, "access")

    # Use CRUD operation instead of direct query
    function_history = crud.function_history.get_function_history(
        db=db, function_id=function_id, skip=skip, limit=limit, flowId=flowId
    )

    return function_history


@router.get(
    "/{function_id}/history/{history_id}",
    response_model=schemas.function_history.FunctionHistory,
    dependencies=[jwt_auth],
)
def read_function_history_by_id(
    *,
    db: Session = Depends(get_db),
    function_id: int,
    history_id: int,
    current_user: User = jwt_auth
) -> Any:
    """
    Get a specific function history entry by ID.
    """
    # First verify the function exists and user has access to it
    function = crud.function.get_function(db=db, function_id=function_id)

    # Check permissions - will raise HTTPException if not allowed
    check_resource_permissions(db, current_user, function, "access")

    # Get the specific history entry
    history_entry = crud.function_history.get_function_history_by_id(
        db=db, history_id=history_id
    )

    return history_entry
