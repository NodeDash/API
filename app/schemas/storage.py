from typing import Optional
from pydantic import BaseModel
from datetime import datetime


# Base schema for shared properties
class StorageBase(BaseModel):
    name: str
    type: str  # 'influxdb', 'mongodb', etc.
    host: str
    port: int
    database: str
    username: str
    password: str


# Schema for creating a storage
class StorageCreate(StorageBase):
    pass


# Schema for updating a storage
class StorageUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    host: Optional[str] = None
    port: Optional[int] = None
    database: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None


# Schema for reading a storage (response model)
class Storage(StorageBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True  # Changed from orm_mode = True for Pydantic v2
