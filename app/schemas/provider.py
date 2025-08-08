from datetime import datetime
from typing import Dict, Optional, Any, List
from pydantic import BaseModel, Field
from app.models.enums import ProviderType, OwnerType


# Shared properties
class ProviderBase(BaseModel):
    name: str
    description: Optional[str] = None
    provider_type: ProviderType
    config: Optional[Dict[str, Any]] = None
    is_active: bool = True


# Properties to receive on provider creation
class ProviderCreate(ProviderBase):
    name: str = Field(..., example="My Provider")
    description: Optional[str] = Field(None, example="This is my provider")
    provider_type: ProviderType = Field(..., example=ProviderType.chirpstack)
    config: Dict[str, Any] = Field(..., example={"key": "value"})
    is_active: bool = Field(True, example=True)
    owner_type: OwnerType = Field(..., example=OwnerType.USER)
    owner_id: int = Field(..., example="12345")


# Properties to receive on provider update
class ProviderUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    provider_type: Optional[ProviderType] = None
    config: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


# Properties to return to client
class Provider(ProviderBase):
    id: int
    owner_id: int
    owner_type: OwnerType
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True
        from_attributes = True
