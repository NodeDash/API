from typing import Dict, Optional, Any
from pydantic import BaseModel
from datetime import datetime
from enum import Enum
from app.models.enums import IntegrationStatus


class IntegrationType(str, Enum):
    HTTP = "http"
    MQTT = "mqtt"


# Base schema for shared properties
class IntegrationBase(BaseModel):
    name: str
    type: IntegrationType
    config: Dict[str, Any]
    status: Optional[IntegrationStatus] = IntegrationStatus.INACTIVE


# Schema for creating an integration
class IntegrationCreate(IntegrationBase):
    pass


# Schema for updating an integration
class IntegrationUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[IntegrationType] = None
    config: Optional[Dict[str, Any]] = None
    status: Optional[IntegrationStatus] = None


# Schema for reading an integration (response model)
class Integration(IntegrationBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True  # Changed from orm_mode = True for Pydantic v2
