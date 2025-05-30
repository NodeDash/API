from typing import List, Optional
from pydantic import BaseModel, Field, validator
from datetime import datetime
from app.models.enums import DeviceStatus, Region


# Base schema for shared properties
class DeviceBase(BaseModel):
    name: str
    dev_eui: str = Field(..., min_length=16, max_length=16)
    app_eui: str = Field(..., min_length=16, max_length=16)
    app_key: str = Field(..., min_length=32, max_length=32)
    region: Optional[Region] = Region.EU868
    is_class_c: Optional[bool] = False
    status: Optional[DeviceStatus] = DeviceStatus.NEVER_SEEN
    expected_transmit_time: Optional[int] = Field(
        None,
        description="Expected transmit time in minutes, between 1 minute and 24 hours (1-1440)",
        ge=1,
        le=1440,
    )

    @validator("expected_transmit_time", pre=True)
    def validate_expected_transmit_time(cls, value):
        """Validate expected_transmit_time is within valid range"""
        if value is None:
            return None
        # Ensure value is an integer between 1 and 1440 (1 minute to 24 hours)
        if not isinstance(value, int):
            try:
                value = int(value)
            except (TypeError, ValueError):
                raise ValueError("Expected transmit time must be an integer")
        if value < 1 or value > 1440:
            raise ValueError(
                "Expected transmit time must be between 1 and 1440 minutes"
            )
        return value


# Schema for creating a device
class DeviceCreate(DeviceBase):
    label_ids: Optional[List[int]] = []

    def __init__(self, **data):
        # Handle labelsId by mapping it to label_ids if provided
        if "labelsId" in data and data["labelsId"] is not None:
            data["label_ids"] = data.pop("labelsId")
        super().__init__(**data)


# Schema for updating a device
class DeviceUpdate(BaseModel):
    name: Optional[str] = None
    dev_eui: Optional[str] = Field(None, min_length=16, max_length=16)
    app_eui: Optional[str] = Field(None, min_length=16, max_length=16)
    app_key: Optional[str] = Field(None, min_length=32, max_length=32)
    region: Optional[Region] = Region.EU868
    is_class_c: Optional[bool] = None
    status: Optional[DeviceStatus] = None
    expected_transmit_time: Optional[int] = Field(
        None,
        description="Expected transmit time in minutes, between 1 minute and 24 hours (1-1440)",
        ge=1,
        le=1440,
    )
    label_ids: Optional[List[int]] = None

    @validator("expected_transmit_time", pre=True)
    def validate_expected_transmit_time(cls, value):
        """Validate expected_transmit_time is within valid range"""
        if value is None:
            return None
        # Ensure value is an integer between 1 and 1440 (1 minute to 24 hours)
        if not isinstance(value, int):
            try:
                value = int(value)
            except (TypeError, ValueError):
                raise ValueError("Expected transmit time must be an integer")
        if value < 1 or value > 1440:
            raise ValueError(
                "Expected transmit time must be between 1 and 1440 minutes"
            )
        return value

    def __init__(self, **data):
        # Handle labelsId by mapping it to label_ids if provided
        if "labelsId" in data and data["labelsId"] is not None:
            data["label_ids"] = data.pop("labelsId")
        super().__init__(**data)


# Schema for reading a device (response model)
class Device(DeviceBase):
    id: int
    created_at: datetime
    updated_at: datetime
    label_ids: List[int] = []  # Only return label_ids, not labelsId

    class Config:
        from_attributes = True
