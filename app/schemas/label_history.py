from typing import Optional, Any
from pydantic import BaseModel
from datetime import datetime


# Base schema for shared properties
class LabelHistoryBase(BaseModel):
    label_id: int
    status: Optional[str] = None  # Status can be used to track label state
    flow_id: Optional[int] = None
    event: str
    data: Optional[Any] = None


# Schema for creating a label history entry
class LabelHistoryCreate(LabelHistoryBase):
    pass


# Brief label info schema for nested relationships
class LabelBrief(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True


# Brief flow info schema for nested relationships
class FlowBrief(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True


# Schema for reading a label history entry (response model)
class LabelHistory(LabelHistoryBase):
    id: int
    timestamp: datetime
    label: Optional[LabelBrief] = None
    flow: Optional[FlowBrief] = None

    class Config:
        from_attributes = True
