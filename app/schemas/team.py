from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class TeamBase(BaseModel):
    name: str


class TeamCreate(TeamBase):
    pass


class TeamUpdate(BaseModel):
    name: Optional[str] = None
    user_ids: Optional[List[int]] = None


class TeamInDBBase(TeamBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True


class Team(TeamInDBBase):
    pass


class TeamWithUsers(TeamInDBBase):
    users: List["UserBase"] = []


from app.schemas.user import UserBase

TeamWithUsers.update_forward_refs()
