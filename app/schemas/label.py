from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime


# Base schema for shared properties
class LabelBase(BaseModel):
    name: str


# Schema for creating a label
class LabelCreate(LabelBase):
    device_ids: Optional[List[int]] = []


# Schema for updating a label
class LabelUpdate(BaseModel):
    name: Optional[str] = None
    device_ids: Optional[List[int]] = None


# Schema for reading a label (response model)
class Label(LabelBase):
    id: int
    created_at: datetime
    updated_at: datetime
    device_ids: List[int] = []  # Only return device_ids, not device_ids

    class Config:
        from_attributes = True  # Changed from orm_mode = True for Pydantic v2


# Schema for adding a device to a label
class DeviceToLabel(BaseModel):
    device_id: int
