from typing import Any, Dict, List, Optional
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


# Operation schemas for storage provider endpoints (InfluxDB write/query/delete)
class WritePoint(BaseModel):
    measurement: str
    tags: Optional[Dict[str, str]] = None
    fields: Dict[str, Any]
    timestamp: Optional[str] = None
    precision: Optional[str] = None


class WritePointsBody(BaseModel):
    points: List[WritePoint]
    bucket: Optional[str] = None


class QueryParams(BaseModel):
    start: str
    end: Optional[str] = None
    measurement: Optional[str] = None
    tags: Optional[Dict[str, str]] = None
    fields: Optional[List[str]] = None
    agg: Optional[str] = None
    window: Optional[str] = None
    limit: Optional[int] = 100
    offset: Optional[int] = 0
    order: Optional[str] = "desc"
    bucket: Optional[str] = None


class UpsertBody(BaseModel):
    measurement: str
    tags: Dict[str, str]
    fields: Dict[str, Any]
    timestamp: str
    precision: Optional[str] = None
    bucket: Optional[str] = None


class DeleteBody(BaseModel):
    start: str
    end: str
    measurement: Optional[str] = None
    predicate: Optional[str] = None
    tags: Optional[Dict[str, str]] = None
    bucket: Optional[str] = None
