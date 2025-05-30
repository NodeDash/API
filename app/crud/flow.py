from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from sqlalchemy import or_

from app.models.flow import Flow
from app.models.team import Team
from app.schemas.flow import FlowCreate, FlowUpdate
from app.models.enums import OwnerType


def get_flow(
    db: Session,
    flow_id: int,
    owner_id: Optional[int] = None,
    owner_type: Optional[str] = None,
    team_id: Optional[int] = None,
) -> Optional[Flow]:
    """
    Get a flow by ID with optional owner filtering

    If owner_id is provided with owner_type=USER, filter by user ownership
    If team_id is provided, filter by team ownership
    """
    query = db.query(Flow).filter(Flow.id == flow_id)

    # Filter by owner if owner parameters are provided
    if owner_id is not None and owner_type == OwnerType.USER:
        query = query.filter(
            Flow.owner_id == owner_id, Flow.owner_type == OwnerType.USER
        )
    elif team_id is not None:
        query = query.filter(
            Flow.owner_id == team_id, Flow.owner_type == OwnerType.TEAM
        )

    return query.first()


def get_flow_by_name(
    db: Session,
    name: str,
    owner_id: Optional[int] = None,
    owner_type: Optional[str] = None,
    team_id: Optional[int] = None,
) -> Optional[Flow]:
    """
    Get a flow by name with optional owner filtering

    If owner_id is provided with owner_type=USER, filter by user ownership
    If team_id is provided, filter by team ownership
    """
    query = db.query(Flow).filter(Flow.name == name)

    # Filter by owner if owner parameters are provided
    if owner_id is not None and owner_type == OwnerType.USER:
        query = query.filter(
            Flow.owner_id == owner_id, Flow.owner_type == OwnerType.USER
        )
    elif team_id is not None:
        query = query.filter(
            Flow.owner_id == team_id, Flow.owner_type == OwnerType.TEAM
        )

    return query.first()


def get_flows(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    owner_id: Optional[int] = None,
    owner_type: Optional[str] = None,
    team_id: Optional[int] = None,
) -> List[Flow]:
    """
    Get all flows with optional owner filtering

    If owner_id is provided with owner_type=USER, filter by user ownership
    If team_id is provided, filter by team ownership
    If owner_id is provided with owner_type=None, get both user owned and team owned flows where user is a member
    """
    query = db.query(Flow)

    # Filter by owner if owner parameters are provided
    if owner_id is not None and owner_type == OwnerType.USER:
        query = query.filter(
            Flow.owner_id == owner_id, Flow.owner_type == OwnerType.USER
        )
    elif team_id is not None:
        query = query.filter(
            Flow.owner_id == team_id, Flow.owner_type == OwnerType.TEAM
        )
    elif owner_id is not None and not owner_type:
        # Get user's flows and team flows where user is a member
        user_teams = db.query(Team).filter(Team.users.any(id=owner_id)).all()
        team_ids = [team.id for team in user_teams]

        # Union of user's flows and team flows
        if team_ids:
            query = query.filter(
                or_(
                    (Flow.owner_id == owner_id) & (Flow.owner_type == OwnerType.USER),
                    (Flow.owner_id.in_(team_ids)) & (Flow.owner_type == OwnerType.TEAM),
                )
            )
        else:
            query = query.filter(
                Flow.owner_id == owner_id, Flow.owner_type == OwnerType.USER
            )

    return query.offset(skip).limit(limit).all()


def create_flow(
    db: Session,
    flow: FlowCreate,
    owner_id: Optional[int] = None,
    owner_type: Optional[str] = OwnerType.USER,
    team_id: Optional[int] = None,
) -> Flow:
    """
    Create a new flow with optional owner assignment

    If owner_id is provided with owner_type=USER, assign user ownership
    If team_id is provided, assign team ownership
    """
    db_flow = Flow(**flow.dict())

    # Assign owner based on parameters
    if owner_id is not None and owner_type == OwnerType.USER:
        db_flow.owner_id = owner_id
        db_flow.owner_type = OwnerType.USER
    elif team_id is not None:
        db_flow.owner_id = team_id
        db_flow.owner_type = OwnerType.TEAM

    db.add(db_flow)
    db.commit()
    db.refresh(db_flow)
    return db_flow


def update_flow(db: Session, db_flow: Flow, flow: FlowUpdate) -> Flow:
    # Convert flow to dictionary, excluding None values
    update_data = flow.dict(exclude_unset=True)

    # Update flow attributes
    for field, value in update_data.items():
        setattr(db_flow, field, value)

    db.add(db_flow)
    db.commit()
    db.refresh(db_flow)
    return db_flow


def delete_flow(db: Session, db_flow: Flow) -> Flow:
    # First, delete all history records associated with this flow
    from app.models.flow_history import FlowHistory

    db.query(FlowHistory).filter(FlowHistory.flow_id == db_flow.id).delete()

    # Then delete the flow itself
    db.delete(db_flow)
    db.commit()
    return db_flow
