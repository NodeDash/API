from typing import Optional, Dict, Any
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
class DeviceHistoryBase(BaseModel):
    device_id: int
    event: str  # "uplink", "downlink", "status_change", etc.
    data: Dict[str, Any]

    # Add validator to ensure data is a dictionary
    _normalize_data = validator("data", pre=True, allow_reuse=True)(ensure_dict)


# Schema for creating a device history entry
class DeviceHistoryCreate(DeviceHistoryBase):
    pass


# Brief device info schema for nested relationships
class DeviceBrief(BaseModel):
    id: int
    name: str
    dev_eui: str

    class Config:
        from_attributes = True


# Schema for reading a device history entry (response model)
class DeviceHistory(DeviceHistoryBase):
    id: int
    timestamp: datetime
    device: Optional[DeviceBrief] = None

    class Config:
        from_attributes = True  # For Pydantic v2
