"""
CRUD operations for device history.
"""

from typing import List, Optional
from sqlalchemy.orm import Session

from app.models.device_history import DeviceHistory


def get_device_history_by_id(db: Session, history_id: int) -> Optional[DeviceHistory]:
    """
    Get a specific device history entry by ID.

    Args:
        db: Database session
        history_id: ID of the history entry to retrieve

    Returns:
        DeviceHistory object or None if not found
    """
    return db.query(DeviceHistory).filter(DeviceHistory.id == history_id).first()


def get_device_history(
    db: Session,
    device_id: Optional[int] = None,
    device_ids: Optional[List[int]] = None,
    flowId: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
) -> List[DeviceHistory]:
    """
    Get device history entries with filtering options.

    Args:
        db: Database session
        device_id: Optional filter by specific device ID
        device_ids: Optional filter by list of device IDs
        skip: Number of records to skip (pagination)
        limit: Maximum number of records to return

    Returns:
        List of DeviceHistory objects
    """
    query = db.query(DeviceHistory)

    # Apply filters
    if device_id is not None:
        query = query.filter(DeviceHistory.device_id == device_id)
    elif device_ids is not None and device_ids:
        query = query.filter(DeviceHistory.device_id.in_(device_ids))

    if flowId is not None:
        query = query.filter(DeviceHistory.flow_id == flowId)

    # Apply sorting and pagination
    return (
        query.order_by(DeviceHistory.timestamp.desc()).offset(skip).limit(limit).all()
    )


def get_latest_device_history(db: Session, device_id: int) -> Optional[DeviceHistory]:
    """
    Get the latest device history entry for a specific device.

    Args:
        db: Database session
        device_id: ID of the device

    Returns:
        The latest DeviceHistory object or None if not found
    """
    return (
        db.query(DeviceHistory)
        .filter(DeviceHistory.device_id == device_id)
        .order_by(DeviceHistory.timestamp.desc())
        .first()
    )


def create_device_history(
    db: Session, device_id: int, event: str, data: dict
) -> DeviceHistory:
    """
    Create a new device history entry.

    Args:
        db: Database session
        device_id: ID of the device
        event: Event type (e.g., 'uplink', 'downlink', 'status_change')
        data: Dictionary containing event data

    Returns:
        The created DeviceHistory object
    """
    device_history = DeviceHistory(device_id=device_id, event=event, data=data)
    db.add(device_history)
    db.commit()
    db.refresh(device_history)
    return device_history
