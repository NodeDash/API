from typing import Optional, Dict, Any, Union
from pydantic import BaseModel, validator
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


# Base schema for shared properties
class FunctionHistoryBase(BaseModel):
    function_id: int
    flow_id: Optional[int] = None  # New field for tracking flow ID
    status: str  # "success", "error"
    input_data: Optional[Dict[str, Any]] = None
    output_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    execution_time: Optional[int] = None  # in milliseconds

    # Add validators to ensure input_data and output_data are dictionaries
    _normalize_input_data = validator("input_data", pre=True, allow_reuse=True)(
        ensure_dict
    )
    _normalize_output_data = validator("output_data", pre=True, allow_reuse=True)(
        ensure_dict
    )


# Schema for creating a function history entry
class FunctionHistoryCreate(FunctionHistoryBase):
    pass


# Brief function info schema for nested relationships
class FunctionBrief(BaseModel):
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


# Schema for reading a function history entry (response model)
class FunctionHistory(FunctionHistoryBase):
    id: int
    timestamp: datetime
    function: Optional[FunctionBrief] = None
    flow: Optional[FlowBrief] = None  # New field for flow relationship

    class Config:
        from_attributes = True  # For Pydantic v2
