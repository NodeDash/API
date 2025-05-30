from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from sqlalchemy import or_

from app.models.integration import Integration
from app.models.integration_history import IntegrationHistory
from app.models.team import Team
from app.schemas.integration import IntegrationCreate, IntegrationUpdate
from app.models.enums import OwnerType


def get_integration(
    db: Session,
    integration_id: int,
    owner_id: Optional[int] = None,
    owner_type: Optional[str] = None,
    team_id: Optional[int] = None,
) -> Optional[Integration]:
    """
    Get an integration by ID with optional owner filtering

    If owner_id is provided with owner_type=USER, filter by user ownership
    If team_id is provided, filter by team ownership
    """
    query = db.query(Integration).filter(Integration.id == integration_id)

    # Filter by owner if owner parameters are provided
    if owner_id is not None and owner_type == OwnerType.USER:
        query = query.filter(
            Integration.owner_id == owner_id, Integration.owner_type == OwnerType.USER
        )
    elif team_id is not None:
        query = query.filter(
            Integration.owner_id == team_id, Integration.owner_type == OwnerType.TEAM
        )

    return query.first()


def get_integration_by_name(
    db: Session,
    name: str,
    owner_id: Optional[int] = None,
    owner_type: Optional[str] = None,
    team_id: Optional[int] = None,
) -> Optional[Integration]:
    """
    Get an integration by name with optional owner filtering

    If owner_id is provided with owner_type=USER, filter by user ownership
    If team_id is provided, filter by team ownership
    """
    query = db.query(Integration).filter(Integration.name == name)

    # Filter by owner if owner parameters are provided
    if owner_id is not None and owner_type == OwnerType.USER:
        query = query.filter(
            Integration.owner_id == owner_id, Integration.owner_type == OwnerType.USER
        )
    elif team_id is not None:
        query = query.filter(
            Integration.owner_id == team_id, Integration.owner_type == OwnerType.TEAM
        )

    return query.first()


def get_integrations(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    owner_id: Optional[int] = None,
    owner_type: Optional[str] = None,
    team_id: Optional[int] = None,
) -> List[Integration]:
    """
    Get all integrations with optional owner filtering

    If owner_id is provided with owner_type=USER, filter by user ownership
    If team_id is provided, filter by team ownership
    If owner_id is provided with owner_type=None, get both user owned and team owned integrations where user is a member
    """
    query = db.query(Integration)

    # Filter by owner if owner parameters are provided
    if owner_id is not None and owner_type == OwnerType.USER:
        query = query.filter(
            Integration.owner_id == owner_id, Integration.owner_type == OwnerType.USER
        )
    elif team_id is not None:
        query = query.filter(
            Integration.owner_id == team_id, Integration.owner_type == OwnerType.TEAM
        )
    elif owner_id is not None and not owner_type:
        # Get user's integrations and team integrations where user is a member
        user_teams = db.query(Team).filter(Team.users.any(id=owner_id)).all()
        team_ids = [team.id for team in user_teams]

        # Union of user's integrations and team integrations
        if team_ids:
            query = query.filter(
                or_(
                    (Integration.owner_id == owner_id)
                    & (Integration.owner_type == OwnerType.USER),
                    (Integration.owner_id.in_(team_ids))
                    & (Integration.owner_type == OwnerType.TEAM),
                )
            )
        else:
            query = query.filter(
                Integration.owner_id == owner_id,
                Integration.owner_type == OwnerType.USER,
            )

    return query.offset(skip).limit(limit).all()


def create_integration(
    db: Session,
    integration: IntegrationCreate,
    owner_id: Optional[int] = None,
    owner_type: Optional[str] = OwnerType.USER,
    team_id: Optional[int] = None,
) -> Integration:
    """
    Create a new integration with optional owner assignment

    If owner_id is provided with owner_type=USER, assign user ownership
    If team_id is provided, assign team ownership
    """
    db_integration = Integration(**integration.dict())

    # Assign owner based on parameters
    if owner_id is not None and owner_type == OwnerType.USER:
        db_integration.owner_id = owner_id
        db_integration.owner_type = OwnerType.USER
    elif team_id is not None:
        db_integration.owner_id = team_id
        db_integration.owner_type = OwnerType.TEAM

    db.add(db_integration)
    db.commit()
    db.refresh(db_integration)
    return db_integration


def update_integration(
    db: Session, db_integration: Integration, integration: IntegrationUpdate
) -> Integration:
    # Convert integration to dictionary, excluding None values
    update_data = integration.dict(exclude_unset=True)

    # Update integration attributes
    for field, value in update_data.items():
        setattr(db_integration, field, value)

    db.add(db_integration)
    db.commit()
    db.refresh(db_integration)
    return db_integration


def delete_integration(db: Session, db_integration: Integration) -> Integration:
    # First, delete all history records associated with this integration
    db.query(IntegrationHistory).filter(
        IntegrationHistory.integration_id == db_integration.id
    ).delete()

    # Then delete the integration itself
    db.delete(db_integration)
    db.commit()
    return db_integration
