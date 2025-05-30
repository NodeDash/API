from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from app.models.team import Team, team_user
from app.models.user import User
from app.schemas.team import TeamCreate, TeamUpdate
from app.models.device import Device
from app.models.flow import Flow
from app.models.integration import Integration
from app.models.label import Label
from app.models.function import Function
from app.models.enums import OwnerType


def get_team(db: Session, team_id: int) -> Optional[Team]:
    """Get a team by ID"""
    return db.query(Team).filter(Team.id == team_id).first()


def get_team_by_name(db: Session, name: str) -> Optional[Team]:
    """Get a team by name"""
    return db.query(Team).filter(Team.name == name).first()


def get_teams(db: Session, skip: int = 0, limit: int = 100) -> List[Team]:
    """Get all teams"""
    return db.query(Team).offset(skip).limit(limit).all()


def get_user_teams(
    db: Session, user_id: int, skip: int = 0, limit: int = 100
) -> List[Team]:
    """Get all teams that a user is a member of"""
    return (
        db.query(Team)
        .filter(Team.users.any(User.id == user_id))
        .offset(skip)
        .limit(limit)
        .all()
    )


def create_team(db: Session, team: TeamCreate, owner_id: int) -> Team:
    """Create a new team"""
    db_team = Team(name=team.name)
    db.add(db_team)
    db.commit()
    db.refresh(db_team)

    # Add the creator as a team member
    user = db.query(User).filter(User.id == owner_id).first()
    if user:
        db_team.users.append(user)
        db.commit()
        db.refresh(db_team)

    return db_team


def update_team(db: Session, db_team: Team, team_update: TeamUpdate) -> Team:
    """Update a team's details"""
    update_data = team_update.dict(exclude_unset=True)

    # Handle user_ids separately
    user_ids = update_data.pop("user_ids", None)

    # Update team attributes
    for field, value in update_data.items():
        setattr(db_team, field, value)

    # Update team members if provided
    if user_ids is not None:
        # Get all users with the provided IDs
        users = db.query(User).filter(User.id.in_(user_ids)).all()
        db_team.users = users

    db.add(db_team)
    db.commit()
    db.refresh(db_team)
    return db_team


def delete_team(db: Session, db_team: Team) -> Team:
    # we need to delete any team members first, then any devices, labels. flows, functions, integrations

    """Delete a team"""
    db.delete(db_team)
    db.commit()
    return db_team


def add_user_to_team(db: Session, team_id: int, user_id: int) -> bool:
    """Add a user to a team"""
    team = get_team(db, team_id)
    user = db.query(User).filter(User.id == user_id).first()

    if not team or not user:
        return False

    if user not in team.users:
        team.users.append(user)
        db.commit()

    return True


def remove_user_from_team(db: Session, team_id: int, user_id: int) -> bool:
    """Remove a user from a team"""
    team = get_team(db, team_id)
    user = db.query(User).filter(User.id == user_id).first()

    if not team or not user:
        return False

    if user in team.users:
        team.users.remove(user)
        db.commit()

    return True


def is_user_in_team(db: Session, team_id: int, user_id: int) -> bool:
    """Check if a user is in a team"""
    team = get_team(db, team_id)

    if not team:
        return False

    return any(user.id == user_id for user in team.users)


def has_team_resources(db: Session, team_id: int) -> bool:
    # Check if a team has any resources (devices, flows, functions, integrations)

    devices = (
        db.query(Device)
        .filter(Device.owner_type == OwnerType.TEAM, Device.owner_id == team_id)
        .first()
    )
    if devices:
        return True
    flows = (
        db.query(Flow)
        .filter(Flow.owner_type == OwnerType.TEAM, Flow.owner_id == team_id)
        .first()
    )
    if flows:
        return True
    functions = (
        db.query(Function)
        .filter(Function.owner_type == OwnerType.TEAM, Function.owner_id == team_id)
        .first()
    )
    if functions:
        return True
    integrations = (
        db.query(Integration)
        .filter(
            Integration.owner_type == OwnerType.TEAM, Integration.owner_id == team_id
        )
        .first()
    )
    if integrations:
        return True
    labels = (
        db.query(Label)
        .filter(Label.owner_type == OwnerType.TEAM, Label.owner_id == team_id)
        .first()
    )
    if labels:
        return True
    return False


def get_team_users(
    db: Session, team_id: int, skip: int = 0, limit: int = 100
) -> List[Dict[str, Any]]:
    """Get all users in a team"""
    team = get_team(db, team_id)
    if not team:
        return []

    # Use the association table to get user details
    users = (
        db.query(User)
        .join(team_user)
        .filter(team_user.c.team_id == team_id)
        .offset(skip)
        .limit(limit)
        .all()
    )

    return [{"id": user.id, "name": user.name} for user in users]


def get_team_user_count(db: Session, team_id: int) -> int:
    """Get the count of users in a team"""
    team = get_team(db, team_id)
    if not team:
        return 0

    # Use the association table to get user count
    user_count = db.query(team_user).filter(team_user.c.team_id == team_id).count()

    return user_count
