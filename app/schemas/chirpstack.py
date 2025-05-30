"""
Schema definitions for ChirpStack API interactions.
"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime


class UplinkChirpstack(BaseModel):
    deduplicationId: Optional[str] = None
    phy_payload: Optional[Dict[str, Any]] = {}
    metadata: Optional[Dict[str, Any]] = {}
    time: Optional[str] = None
    deviceInfo: Optional[Dict[str, Any]] = {}
    object: Optional[Dict[str, Any]] = {}
    devAddr: Optional[str] = None
    adr: Optional[bool] = None
    dr: Optional[int] = None
    fCnt: Optional[int] = None
    fPort: Optional[int] = None
    confirmed: Optional[bool] = None
    data: Optional[str] = None
    rxInfo: Optional[List[Dict[str, Any]]] = []
    txInfo: Optional[Dict[str, Any]] = {}


class DeviceDownlink(BaseModel):
    """Schema for device downlink queue item."""

    data: str = Field(..., description="Hex encoded payload data")
    confirmed: bool = Field(
        False, description="Whether the downlink requires confirmation"
    )
    f_port: int = Field(1, description="FPort to use (1-223)")


class DeviceActivation(BaseModel):
    """Schema for device activation (ABP)."""

    dev_addr: str = Field(..., description="Device address (4 bytes)")
    app_s_key: str = Field(..., description="Application session key (16 bytes)")
    nwk_s_enc_key: str = Field(
        ..., description="Network session encryption key (16 bytes)"
    )
    s_nwk_s_int_key: str = Field(
        ..., description="Serving network session integrity key (16 bytes)"
    )
    f_nwk_s_int_key: str = Field(
        ..., description="Forwarding network session integrity key (16 bytes)"
    )
    fcnt_up: int = Field(0, description="Uplink frame counter")
    fcnt_down: int = Field(0, description="Downlink frame counter")


class DeviceKeysUpdate(BaseModel):
    """Schema for updating device keys."""

    nwk_key: str = Field(..., description="Network key (16 bytes)")
    app_key: str = Field(..., description="Application key (16 bytes)")


class GatewayStats(BaseModel):
    """Schema for gateway statistics."""

    timestamp: str
    rxPacketsReceived: int
    rxPacketsReceivedOK: int
    txPacketsReceived: int
    txPacketsEmitted: int


"""
Schemas for ChirpStack configuration.
"""


class ChirpStackConfigBase(BaseModel):
    """Base schema for ChirpStack configuration"""

    name: str = Field(..., description="Name for this ChirpStack configuration")
    server_url: str = Field(..., description="ChirpStack server URL")
    api_key: str = Field(..., description="ChirpStack API key")
    application_id: Optional[str] = Field(None, description="ChirpStack application ID")
    description: Optional[str] = Field(
        None, description="Description for this configuration"
    )
    device_profiles: Optional[Dict[str, str]] = Field(
        default_factory=dict, description="Dictionary of device profiles"
    )
    is_active: bool = Field(
        default=False,
        description="Flag to indicate if this is the active configuration",
    )


class ChirpStackConfigCreate(ChirpStackConfigBase):
    """Schema for creating a new ChirpStack configuration"""

    pass


class ChirpStackConfigUpdate(BaseModel):
    """Schema for updating an existing ChirpStack configuration"""

    name: Optional[str] = None
    server_url: Optional[str] = None
    api_key: Optional[str] = None
    application_id: Optional[str] = None
    description: Optional[str] = None
    device_profiles: Optional[Dict[str, str]] = None
    is_active: Optional[bool] = None


class ChirpStackConfig(ChirpStackConfigBase):
    """Schema for a complete ChirpStack configuration with DB fields"""

    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


"""
Schemas for ChirpStack device management.
"""


class DeviceBase(BaseModel):
    """Base schema for ChirpStack device"""

    name: str = Field(..., description="Device name")
    description: Optional[str] = Field("", description="Device description")
    dev_eui: str = Field(..., description="Device EUI (8 bytes hex)")
    app_eui: str = Field(..., description="Application EUI (8 bytes hex)")
    skip_fcnt_check: bool = Field(False, description="Skip frame counter check")
    is_active: bool = Field(True, description="Whether the device is enabled")
    tags: Optional[Dict[str, str]] = Field(
        default_factory=dict, description="Device tags"
    )


class DeviceKeys(BaseModel):
    appKey: str = Field(..., description="Application key (16 bytes hex)")
    nwkKey: str = Field(..., description="Network key (16 bytes hex)")


class DeviceCreate(DeviceBase):
    """Schema for creating a new ChirpStack device"""

    pass


class ChirpStackDeviceCreate(BaseModel):
    """Schema for creating a device in ChirpStack API"""

    name: str = Field(..., description="Device name")
    dev_eui: str = Field(..., description="Device EUI (8 bytes hex)")
    app_eui: str = Field(..., description="Join EUI/AppEUI (8 bytes hex)")
    description: Optional[str] = Field("", description="Device description")
    device_profile_id: str = Field(..., description="Device profile ID")
    application_id: str = Field(..., description="Application ID")
    skip_fcnt_check: bool = Field(False, description="Skip frame counter check")
    is_active: bool = Field(True, description="Whether the device is enabled")
    tags: Optional[Dict[str, str]] = Field(
        default_factory=dict, description="Device tags"
    )


class DeviceUpdate(BaseModel):
    """Schema for updating an existing ChirpStack device"""

    name: Optional[str] = None
    description: Optional[str] = None
    device_profile_id: Optional[str] = None
    skip_fcnt_check: Optional[bool] = None
    is_active: Optional[bool] = None
    tags: Optional[Dict[str, str]] = None


class Device(DeviceBase):
    """Schema for a complete ChirpStack device with additional fields"""

    application_id: str
    device_status: Optional[Dict[str, Any]] = None
    last_seen_at: Optional[datetime] = None
    margin: Optional[int] = None
    battery_level: Optional[float] = None

    class Config:
        from_attributes = True


class DeviceListItem(BaseModel):
    """Schema for a device in a list response"""

    dev_eui: str
    name: str
    description: Optional[str] = ""
    application_id: str
    device_profile_id: str
    is_disabled: bool

    class Config:
        from_attributes = True


class DeviceListResponse(BaseModel):
    """Schema for a paginated device list response"""

    total_count: int
    devices: List[DeviceListItem]


"""
Schemas for ChirpStack device profile management.
"""


class DeviceProfileBase(BaseModel):
    """Base schema for ChirpStack device profile"""

    name: str
    description: str
    region: str
    mac_version: str  # LORAWAN_1_0_0, LORAWAN_1_0_1, etc.
    reg_params_revision: str  # A, B, RP002_1_0_0, etc.
    adr_algorithm_id: Optional[str] = None
    payload_codec_runtime: Optional[str] = None  # NONE, CAYENNE_LPP, JS
    payload_codec_script: Optional[str] = None
    flush_queue_on_activate: Optional[bool] = None
    uplink_interval: Optional[int] = None
    device_status_req_interval: Optional[int] = None
    supports_otaa: Optional[bool] = None
    supports_class_b: Optional[bool] = None
    supports_class_c: Optional[bool] = None
    class_b_timeout: Optional[int] = None
    class_b_ping_slot_nb_k: Optional[int] = None
    class_b_ping_slot_dr: Optional[int] = None
    class_b_ping_slot_freq: Optional[int] = None
    class_c_timeout: Optional[int] = None
    abp_rx1_delay: Optional[int] = None
    abp_rx1_dr_offset: Optional[int] = None
    abp_rx2_dr: Optional[int] = None
    abp_rx2_freq: Optional[int] = None
    tags: Optional[Dict[str, str]] = None
    measurements: Optional[Dict[str, Dict[str, Any]]] = None
    auto_detect_measurements: Optional[bool] = None


class DeviceProfileCreate(DeviceProfileBase):
    """Schema for creating a new ChirpStack device profile"""

    pass


class DeviceProfileUpdate(BaseModel):
    """Schema for updating an existing ChirpStack device profile"""

    name: Optional[str] = None
    description: Optional[str] = None
    region: Optional[str] = None
    mac_version: Optional[str] = None
    reg_params_revision: Optional[str] = None
    adr_algorithm_id: Optional[str] = None
    payload_codec_runtime: Optional[str] = None
    payload_codec_script: Optional[str] = None
    flush_queue_on_activate: Optional[bool] = None
    uplink_interval: Optional[int] = None
    device_status_req_interval: Optional[int] = None
    supports_otaa: Optional[bool] = None
    supports_class_b: Optional[bool] = None
    supports_class_c: Optional[bool] = None
    class_b_timeout: Optional[int] = None
    class_b_ping_slot_nb_k: Optional[int] = None
    class_b_ping_slot_dr: Optional[int] = None
    class_b_ping_slot_freq: Optional[int] = None
    class_c_timeout: Optional[int] = None
    abp_rx1_delay: Optional[int] = None
    abp_rx1_dr_offset: Optional[int] = None
    abp_rx2_dr: Optional[int] = None
    abp_rx2_freq: Optional[int] = None
    tags: Optional[Dict[str, str]] = None
    measurements: Optional[Dict[str, Dict[str, Any]]] = None
    auto_detect_measurements: Optional[bool] = None


class DeviceProfile(DeviceProfileBase):
    """Schema for a complete ChirpStack device profile with additional fields"""

    id: str
    tenant_id: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class DeviceProfileListItem(BaseModel):
    """Schema for a device profile in a list response"""

    id: str
    name: str
    region: str
    mac_version: str
    reg_params_revision: str
    supports_otaa: bool
    supports_class_b: bool
    supports_class_c: bool
    created_at: datetime
    updated_at: datetime


class DeviceProfileListResponse(BaseModel):
    """Schema for a paginated device profile list response"""

    total_count: int
    result: List[DeviceProfileListItem]


"""
Schemas for ChirpStack application management.
"""


class ApplicationBase(BaseModel):
    """Base schema for ChirpStack application."""

    name: str = Field(..., description="Application name")
    description: Optional[str] = Field("", description="Application description")
    tenantId: Optional[str] = Field(
        None, description="Tenant ID this application belongs to"
    )
    tags: Optional[Dict[str, str]] = Field(
        default_factory=dict, description="Application tags"
    )


class ApplicationCreate(ApplicationBase):
    """Schema for creating a new ChirpStack application."""


class ApplicationUpdate(BaseModel):
    """Schema for updating an existing ChirpStack application."""

    name: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[Dict[str, str]] = None


class Application(ApplicationBase):
    """Schema for a complete ChirpStack application."""

    id: str

    class Config:
        from_attributes = True


class ApplicationListItem(BaseModel):
    """Schema for an application in a list response."""

    id: str
    name: str
    description: Optional[str] = ""

    class Config:
        from_attributes = True


class ApplicationListResponse(BaseModel):
    """Schema for a paginated application list response."""

    total_count: int
    applications: List[ApplicationListItem]


"""
Schemas for ChirpStack HTTP integration management.
"""


class HTTPIntegrationBase(BaseModel):
    """Base schema for ChirpStack HTTP integration."""

    headers: Optional[Dict[str, str]] = Field(
        default_factory=dict, description="HTTP headers"
    )
    event_endpoints: Optional[Dict[str, bool]] = Field(
        default_factory=dict,
        description="Event endpoints to enable (e.g., uplink, join, etc.)",
    )


class HTTPIntegrationCreate(HTTPIntegrationBase):
    """Schema for creating a new ChirpStack HTTP integration."""

    application_id: str = Field(
        ..., description="Application ID this integration belongs to"
    )
    endpoint: str = Field(..., description="HTTP endpoint URL")


class HTTPIntegrationUpdate(HTTPIntegrationBase):
    """Schema for updating an existing ChirpStack HTTP integration."""

    endpoint: Optional[str] = None


class HTTPIntegration(HTTPIntegrationBase):
    """Schema for a complete ChirpStack HTTP integration."""

    application_id: str
    endpoint: str

    class Config:
        from_attributes = True
