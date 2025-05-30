from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


# Base schema for shared properties
class IntegrationHistoryBase(BaseModel):
    integration_id: int = Field(..., alias="integrationId")
    flow_id: Optional[int] = Field(
        None, alias="flowId"
    )  # New field for tracking flow ID
    status: str  # "success", "error"
    input_data: Optional[Dict[str, Any]] = Field(None, alias="inputData")
    response_data: Optional[Dict[str, Any]] = Field(None, alias="responseData")
    error_message: Optional[str] = Field(None, alias="errorMessage")
    execution_time: Optional[int] = Field(
        None, alias="executionTimeMs"
    )  # in milliseconds


# Schema for creating an integration history entry
class IntegrationHistoryCreate(IntegrationHistoryBase):
    pass


# Brief integration info schema for nested relationships
class IntegrationBrief(BaseModel):
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


# Schema for reading an integration history entry (response model)
class IntegrationHistory(IntegrationHistoryBase):
    id: int
    timestamp: datetime
    integration: Optional[IntegrationBrief] = None
    flow: Optional[FlowBrief] = None  # New field for flow relationship

    class Config:
        from_attributes = True  # For Pydantic v2
        populate_by_name = True  # Allow population by alias
