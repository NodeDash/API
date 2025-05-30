from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from sqlalchemy import or_

from app.models.function import Function
from app.models.team import Team
from app.schemas.function import FunctionCreate, FunctionUpdate
from app.models.enums import OwnerType


def get_function(
    db: Session,
    function_id: int,
    owner_id: Optional[int] = None,
    owner_type: Optional[str] = None,
    team_id: Optional[int] = None,
) -> Optional[Function]:
    """
    Get a function by ID with optional owner filtering

    If owner_id is provided with owner_type=USER, filter by user ownership
    If team_id is provided, filter by team ownership
    """
    query = db.query(Function).filter(Function.id == function_id)

    # Filter by owner if owner parameters are provided
    if owner_id is not None and owner_type == OwnerType.USER:
        query = query.filter(
            Function.owner_id == owner_id, Function.owner_type == OwnerType.USER
        )
    elif team_id is not None:
        query = query.filter(
            Function.owner_id == team_id, Function.owner_type == OwnerType.TEAM
        )

    return query.first()


def get_function_by_name(
    db: Session,
    name: str,
    owner_id: Optional[int] = None,
    owner_type: Optional[str] = None,
    team_id: Optional[int] = None,
) -> Optional[Function]:
    """
    Get a function by name with optional owner filtering

    If owner_id is provided with owner_type=USER, filter by user ownership
    If team_id is provided, filter by team ownership
    """
    query = db.query(Function).filter(Function.name == name)

    # Filter by owner if owner parameters are provided
    if owner_id is not None and owner_type == OwnerType.USER:
        query = query.filter(
            Function.owner_id == owner_id, Function.owner_type == OwnerType.USER
        )
    elif team_id is not None:
        query = query.filter(
            Function.owner_id == team_id, Function.owner_type == OwnerType.TEAM
        )

    return query.first()


def get_functions(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    owner_id: Optional[int] = None,
    owner_type: Optional[str] = None,
    team_id: Optional[int] = None,
) -> List[Function]:
    """
    Get all functions with optional owner filtering

    If owner_id is provided with owner_type=USER, filter by user ownership
    If team_id is provided, filter by team ownership
    If owner_id is provided with owner_type=None, get both user owned and team owned functions where user is a member
    """
    query = db.query(Function)

    # Filter by owner if owner parameters are provided
    if owner_id is not None and owner_type == OwnerType.USER:
        query = query.filter(
            Function.owner_id == owner_id, Function.owner_type == OwnerType.USER
        )
    elif team_id is not None:
        query = query.filter(
            Function.owner_id == team_id, Function.owner_type == OwnerType.TEAM
        )
    elif owner_id is not None and not owner_type:
        # Get user's functions and team functions where user is a member
        user_teams = db.query(Team).filter(Team.users.any(id=owner_id)).all()
        team_ids = [team.id for team in user_teams]

        # Union of user's functions and team functions
        if team_ids:
            query = query.filter(
                or_(
                    (Function.owner_id == owner_id)
                    & (Function.owner_type == OwnerType.USER),
                    (Function.owner_id.in_(team_ids))
                    & (Function.owner_type == OwnerType.TEAM),
                )
            )
        else:
            query = query.filter(
                Function.owner_id == owner_id, Function.owner_type == OwnerType.USER
            )

    return query.offset(skip).limit(limit).all()


def create_function(
    db: Session,
    function: FunctionCreate,
    owner_id: Optional[int] = None,
    owner_type: Optional[str] = OwnerType.USER,
    team_id: Optional[int] = None,
) -> Function:
    """
    Create a new function with optional owner assignment

    If owner_id is provided with owner_type=USER, assign user ownership
    If team_id is provided, assign team ownership
    """
    db_function = Function(**function.dict())

    # Assign owner based on parameters
    if owner_id is not None and owner_type == OwnerType.USER:
        db_function.owner_id = owner_id
        db_function.owner_type = OwnerType.USER
    elif team_id is not None:
        db_function.owner_id = team_id
        db_function.owner_type = OwnerType.TEAM

    db.add(db_function)
    db.commit()
    db.refresh(db_function)
    return db_function


def update_function(
    db: Session, db_function: Function, function: FunctionUpdate
) -> Function:
    # Convert function to dictionary, excluding None values
    update_data = function.dict(exclude_unset=True)

    # Update function attributes
    for field, value in update_data.items():
        setattr(db_function, field, value)

    db.add(db_function)
    db.commit()
    db.refresh(db_function)
    return db_function


def delete_function(db: Session, db_function: Function) -> Function:
    # First, find and update any flows that reference this function
    from app.models.flow import Flow
    from app.models.function_history import FunctionHistory

    # Get all flows
    flows = db.query(Flow).all()

    for flow in flows:
        modified = False

        # Skip flows without nodes
        if not flow.nodes or not isinstance(flow.nodes, list):
            continue

        # Filter out nodes that reference this function
        updated_nodes = []
        function_nodes_to_remove = []

        for node in flow.nodes:
            # Check if this is a function node referencing the function being deleted
            # Using entityId instead of functionId based on actual flow structure
            if node.get("type") == "function" and str(
                node.get("data", {}).get("entityId")
            ) == str(db_function.id):
                function_nodes_to_remove.append(node.get("id"))
                modified = True
            else:
                updated_nodes.append(node)

        # If we found function nodes to remove, update the flow
        if modified:
            flow.nodes = updated_nodes

            # Also need to remove any edges connected to the removed nodes
            if flow.edges and isinstance(flow.edges, list):
                updated_edges = []

                for edge in flow.edges:
                    # Keep edges that don't connect to the removed nodes
                    if (
                        edge.get("source") not in function_nodes_to_remove
                        and edge.get("target") not in function_nodes_to_remove
                    ):
                        updated_edges.append(edge)

                flow.edges = updated_edges

            # Save the updated flow
            db.add(flow)

    # Delete all history records associated with this function
    db.query(FunctionHistory).filter(
        FunctionHistory.function_id == db_function.id
    ).delete()

    # Now delete the function itself
    db.delete(db_function)
    db.commit()
    return db_function
