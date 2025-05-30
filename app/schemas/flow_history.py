from typing import Optional, Dict, Any, List, Union
from pydantic import BaseModel, validator, Field
from datetime import datetime
import json


def ensure_dict(v):
    """Ensure that the value is a dictionary. If it's a string, try to parse it as JSON."""
    if isinstance(v, dict):
        return v
    if isinstance(v, str):
        try:
            return json.loads(v)
        except json.JSONDecodeError:
            # If we can't parse it as JSON, return it as a dict with a single key
            return {"data": v}
    if v is None:
        return {}
    # If it's any other type, convert to string and wrap in a dict
    return {"data": str(v)}


def ensure_list(v):
    """Ensure that the value is a list. If it's a string, try to parse it as JSON."""
    if isinstance(v, list):
        return v
    if isinstance(v, str):
        try:
            data = json.loads(v)
            if isinstance(data, list):
                return data
            return [data]
        except json.JSONDecodeError:
            # If we can't parse it as JSON, return an empty list
            return []
    if v is None:
        return []
    # If it's any other type, convert to string and wrap in a list
    return [{"data": str(v)}]


def handle_error_details(v):
    """Handle error details which could be a string or list."""
    if v is None:
        return None
    if isinstance(v, str):
        return v
    if isinstance(v, list):
        try:
            return json.dumps(v)
        except (TypeError, ValueError):
            return str(v)
    return str(v)


# Base schema for shared properties
class FlowHistoryBase(BaseModel):
    flow_id: int
    status: str  # "success", "error", "partial"
    trigger_source: Optional[str] = None  # "device_uplink", etc.
    source_id: Optional[int] = None  # ID of the triggering entity (device, etc.)
    execution_path: Optional[List[Dict[str, Any]]] = Field(default_factory=list)
    error_details: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    execution_time: Optional[int] = None  # in milliseconds
    input_data: Optional[Dict[str, Any]] = Field(default_factory=dict)
    output_data: Optional[Dict[str, Any]] = Field(default_factory=dict)
    error: Optional[str] = None

    # Add validators to ensure input_data and output_data are dictionaries
    _normalize_input_data = validator("input_data", pre=True, allow_reuse=True)(
        ensure_dict
    )
    _normalize_output_data = validator("output_data", pre=True, allow_reuse=True)(
        ensure_dict
    )
    # Add validator to ensure execution_path is a list
    _normalize_execution_path = validator("execution_path", pre=True, allow_reuse=True)(
        ensure_list
    )
    # Add validator to handle error_details correctly
    _normalize_error_details = validator("error_details", pre=True, allow_reuse=True)(
        handle_error_details
    )


# Schema for creating a flow history entry
class FlowHistoryCreate(FlowHistoryBase):
    pass


# Brief flow info schema for nested relationships
class FlowBrief(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True


# Schema for reading a flow history entry (response model)
class FlowHistory(FlowHistoryBase):
    id: int
    timestamp: datetime
    flow: Optional[FlowBrief] = None

    class Config:
        from_attributes = True  # For Pydantic v2
