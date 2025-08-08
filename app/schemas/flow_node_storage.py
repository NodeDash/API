from typing import Any, Dict, Optional
from pydantic import BaseModel


class StorageNodeConfig(BaseModel):
    provider_id: int
    measurement: str
    tags: Optional[Dict[str, str]] = None
    fields: Optional[Dict[str, Any]] = None
    bucket: Optional[str] = None
    timestamp: Optional[str] = None
    precision: Optional[str] = None
