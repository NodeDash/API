from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime


class ParameterDefinition(BaseModel):
    name: str
    type: str
    description: Optional[str] = None
    required: bool = False
    default: Optional[Any] = None


# Base schema for shared properties
class FunctionBase(BaseModel):
    name: str
    description: Optional[str] = None
    parameters: Optional[List[ParameterDefinition]] = None
    code: Optional[str] = None
    status: Optional[str] = "inactive"


# Schema for creating a function
class FunctionCreate(FunctionBase):
    pass


# Schema for updating a function
class FunctionUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    parameters: Optional[List[ParameterDefinition]] = None
    code: Optional[str] = None
    status: Optional[str] = None  # Changed from bool to str


# Schema for reading a function (response model)
class Function(FunctionBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True  # Changed from orm_mode = True for Pydantic v2
