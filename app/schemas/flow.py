from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime


# Base schema for shared properties
class FlowBase(BaseModel):
    name: str
    description: Optional[str] = None
    nodes: Optional[List[Dict[str, Any]]] = None
    edges: Optional[List[Dict[str, Any]]] = None
    layout: Optional[Dict[str, Any]] = None


# Schema for creating a flow
class FlowCreate(FlowBase):
    pass


# Schema for updating a flow
class FlowUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    nodes: Optional[List[Dict[str, Any]]] = None
    edges: Optional[List[Dict[str, Any]]] = None
    layout: Optional[Dict[str, Any]] = None


# Schema for reading a flow (response model)
class Flow(FlowBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True  # Changed from orm_mode = True for Pydantic v2
