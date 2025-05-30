from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from app.crud.user import get_by_email
from app.models.user import User
from app.crud import team as crud_team
from app.schemas.team import Team, TeamCreate, TeamUpdate, TeamWithUsers
from app.core.auth import jwt_auth, check_team_membership
from app.db.database import get_db

router = APIRouter()


@router.get("/", response_model=List[Team])
def read_teams(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = jwt_auth,
):
    """
    Retrieve teams.
    """
    # If user is superuser, return all teams
    if current_user.is_superuser:
        teams = crud_team.get_teams(db, skip=skip, limit=limit)
    else:
        # Otherwise return only teams the user is a member of
        teams = crud_team.get_user_teams(
            db, user_id=current_user.id, skip=skip, limit=limit
        )
    return teams


@router.post("/", response_model=Team, status_code=status.HTTP_201_CREATED)
def create_team(
    team_in: TeamCreate, db: Session = Depends(get_db), current_user: User = jwt_auth
):
    """
    Create new team.
    """
    team = crud_team.get_team_by_name(db, name=team_in.name)
    if team:
        raise HTTPException(
            status_code=400,
            detail="A team with this name already exists.",
        )
    return crud_team.create_team(db=db, team=team_in, owner_id=current_user.id)


@router.get("/{team_id}", response_model=TeamWithUsers)
def read_team(
    team_id: int, db: Session = Depends(get_db), current_user: User = jwt_auth
):
    """
    Get team by ID.
    """
    team = crud_team.get_team(db, team_id=team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    # Check if user has access to this team
    check_team_membership(db, current_user, team_id)

    return team


@router.put("/{team_id}", response_model=Team)
def update_team(
    team_id: int,
    team_in: TeamUpdate,
    db: Session = Depends(get_db),
    current_user: User = jwt_auth,
):
    """
    Update a team.
    """
    team = crud_team.get_team(db, team_id=team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    # Check if user has access to this team
    check_team_membership(db, current_user, team_id)

    return crud_team.update_team(db=db, db_team=team, team_update=team_in)


@router.delete("/{team_id}", response_model=Team)
def delete_team(
    team_id: int, db: Session = Depends(get_db), current_user: User = jwt_auth
):
    """
    Delete a team.
    """
    team = crud_team.get_team(db, team_id=team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    # Only superusers can delete teams
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=403, detail="Not enough permissions to delete teams"
        )

    # Check if user has access to this team
    check_team_membership(db, current_user, team_id)

    # Check if team has any devices, flows, functions, or integrations
    if crud_team.has_team_resources(db, team_id):
        raise HTTPException(
            status_code=400,
            detail="Cannot delete team with existing resources. Please delete resources first.",
        )

    return crud_team.delete_team(db=db, db_team=team)


@router.post("/{team_id}/members/{user_email}", status_code=status.HTTP_204_NO_CONTENT)
def add_team_member(
    team_id: int,
    user_email: str,
    db: Session = Depends(get_db),
    current_user: User = jwt_auth,
):
    """
    Add a user to a team.
    """
    team = crud_team.get_team(db, team_id=team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    # Check if user has access to this team
    check_team_membership(db, current_user, team_id)

    # Check if user exists
    user = get_by_email(db, email=user_email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot add yourself to a team")
    if crud_team.is_user_in_team(db, team_id=team_id, user_id=user.id):
        raise HTTPException(
            status_code=400, detail="User is already a member of this team"
        )

    success = crud_team.add_user_to_team(db=db, team_id=team_id, user_id=user.id)
    if not success:
        raise HTTPException(status_code=404, detail="User not found")

    return None


@router.delete("/{team_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_team_member(
    team_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = jwt_auth,
):
    """
    Remove a user from a team.
    """
    team = crud_team.get_team(db, team_id=team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    # Check if user has access to this team
    check_team_membership(db, current_user, team_id)

    team_members = crud_team.get_team_users(db, team_id=team_id)

    # check the count minus the current user
    if len(team_members) <= 1:
        raise HTTPException(
            status_code=400,
            detail="Cannot remove the last member of the team. Please delete the team instead.",
        )
    # Check if user exists
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    success = crud_team.remove_user_from_team(db=db, team_id=team_id, user_id=user_id)
    if not success:
        raise HTTPException(
            status_code=404, detail="User not found or not a member of the team"
        )

    return None
