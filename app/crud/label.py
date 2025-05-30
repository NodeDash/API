from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from sqlalchemy import or_

from app.models.label import Label
from app.models.device import Device
from app.models.team import Team
from app.schemas.label import LabelCreate, LabelUpdate
from app.models.enums import OwnerType


def get_label(
    db: Session,
    label_id: int,
    owner_id: Optional[int] = None,
    owner_type: Optional[str] = None,
    team_id: Optional[int] = None,
) -> Optional[Label]:
    """
    Get a label by ID with optional owner filtering

    If owner_id is provided with owner_type=USER, filter by user ownership
    If team_id is provided, filter by team ownership
    """
    query = db.query(Label).filter(Label.id == label_id)

    # Filter by owner if owner parameters are provided
    if owner_id is not None and owner_type == OwnerType.USER:
        query = query.filter(
            Label.owner_id == owner_id, Label.owner_type == OwnerType.USER
        )
    elif team_id is not None:
        query = query.filter(
            Label.owner_id == team_id, Label.owner_type == OwnerType.TEAM
        )

    label = query.first()
    if label:
        # Manually set device_ids for the response
        setattr(label, "device_ids", [device.id for device in label.devices])
    return label


def get_label_by_name(
    db: Session,
    name: str,
    owner_id: Optional[int] = None,
    owner_type: Optional[str] = None,
    team_id: Optional[int] = None,
) -> Optional[Label]:
    """
    Get a label by name with optional owner filtering

    If owner_id is provided with owner_type=USER, filter by user ownership
    If team_id is provided, filter by team ownership
    """
    query = db.query(Label).filter(Label.name == name)

    # Filter by owner if owner parameters are provided
    if owner_id is not None and owner_type == OwnerType.USER:
        query = query.filter(
            Label.owner_id == owner_id, Label.owner_type == OwnerType.USER
        )
    elif team_id is not None:
        query = query.filter(
            Label.owner_id == team_id, Label.owner_type == OwnerType.TEAM
        )

    label = query.first()
    if label:
        # Manually set device_ids for the response
        setattr(label, "device_ids", [device.id for device in label.devices])
    return label


def get_labels(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    owner_id: Optional[int] = None,
    team_id: Optional[int] = None,
) -> List[Label]:
    """
    Get all labels with optional owner filtering

    If owner_id is provided with owner_type=USER, filter by user ownership
    If team_id is provided, filter by team ownership
    """
    query = db.query(Label)

    # Filter by owner if owner parameters are provided
    if owner_id is not None:
        query = query.filter(
            Label.owner_id == owner_id, Label.owner_type == OwnerType.USER
        )
    elif team_id is not None:
        query = query.filter(
            Label.owner_id == team_id, Label.owner_type == OwnerType.TEAM
        )
    else:
        # no query filter, return error
        raise ValueError("Either owner_id or team_id must be provided")

    labels = query.offset(skip).limit(limit).all()
    # Set device_ids for each label
    for label in labels:
        setattr(label, "device_ids", [device.id for device in label.devices])
    return labels


def create_label(
    db: Session,
    label: LabelCreate,
    owner_id: Optional[int] = None,
    owner_type: Optional[str] = OwnerType.USER,
    team_id: Optional[int] = None,
) -> Label:
    """
    Create a new label with optional owner assignment

    If owner_id is provided with owner_type=USER, assign user ownership
    If team_id is provided, assign team ownership
    """
    # Extract device IDs from the request
    device_ids = label.device_ids or []

    print(f"Creating label with device_ids: {device_ids}")

    # Create a copy of the data excluding device_ids
    label_data = label.dict(exclude={"device_ids"})

    # Create the label
    db_label = Label(**label_data)

    # Assign owner based on parameters
    if owner_id is not None and owner_type == OwnerType.USER:
        db_label.owner_id = owner_id
        db_label.owner_type = OwnerType.USER
    elif team_id is not None:
        db_label.owner_id = team_id
        db_label.owner_type = OwnerType.TEAM

    # Add devices if provided
    if device_ids:
        devices = db.query(Device).filter(Device.id.in_(device_ids)).all()
        db_label.devices = devices
        print(f"Devices added to label: {[device.id for device in devices]}")

    db.add(db_label)
    db.commit()
    db.refresh(db_label)

    # Set device_ids for the response
    setattr(db_label, "device_ids", [device.id for device in db_label.devices])

    return db_label


def update_label(db: Session, db_label: Label, label: LabelUpdate) -> Label:
    # Convert label to dictionary, excluding None values
    update_data = label.dict(exclude_unset=True)

    # Extract device_ids if provided
    device_ids = update_data.pop("device_ids", None)

    # Update label attributes
    for field, value in update_data.items():
        setattr(db_label, field, value)

    # Update devices if provided
    if device_ids is not None:
        devices = db.query(Device).filter(Device.id.in_(device_ids)).all()
        db_label.devices = devices

    db.add(db_label)
    db.commit()
    db.refresh(db_label)

    # Set device_ids for the response
    setattr(db_label, "device_ids", [device.id for device in db_label.devices])

    return db_label


def delete_label(db: Session, db_label: Label) -> Label:
    db.delete(db_label)
    db.commit()
    return db_label


def add_device_to_label(db: Session, db_label: Label, device_id: int) -> Label:
    device = db.query(Device).filter(Device.id == device_id).first()
    if device:
        db_label.devices.append(device)
        db.commit()
        db.refresh(db_label)

    # Set device_ids for the response
    setattr(db_label, "device_ids", [device.id for device in db_label.devices])

    return db_label


def remove_device_from_label(db: Session, db_label: Label, device_id: int) -> Label:
    device = db.query(Device).filter(Device.id == device_id).first()
    if device and device in db_label.devices:
        db_label.devices.remove(device)
        db.commit()
        db.refresh(db_label)

    # Set device_ids for the response
    setattr(db_label, "device_ids", [device.id for device in db_label.devices])

    return db_label
