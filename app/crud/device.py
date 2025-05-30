from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any, Tuple
from datetime import timedelta, datetime

from app.models.device import Device
from app.models.label import Label
from app.models.team import Team
from app.schemas.device import DeviceCreate, DeviceUpdate

from app.models.enums import OwnerType
from app.models.device_history import DeviceHistory
import app.crud.chirpstack as chirpstack
import app.crud.team as crud_team
from app.crud.provider import get_providers

from app.schemas.chirpstack import (
    ChirpStackDeviceCreate,
    DeviceKeys,
)


def get_device(
    db: Session,
    device_id: int,
    owner_id: Optional[int] = None,
    owner_type: Optional[str] = None,
    team_id: Optional[int] = None,
) -> Optional[Device]:
    """
    Get a device by ID with optional owner filtering

    If owner_id is provided with owner_type=USER, filter by user ownership
    If team_id is provided, filter by team ownership
    """
    query = db.query(Device).filter(Device.id == device_id)

    # Filter by owner if owner parameters are provided
    if owner_id is not None and owner_type == OwnerType.USER:
        query = query.filter(
            Device.owner_id == owner_id, Device.owner_type == OwnerType.USER
        )
    elif team_id is not None:
        query = query.filter(
            Device.owner_id == team_id, Device.owner_type == OwnerType.TEAM
        )

    device = query.first()
    if device:
        # Manually set label_ids for the response
        setattr(device, "label_ids", [label.id for label in device.labels])

    return device


def get_device_by_dev_eui(
    db: Session,
    dev_eui: str,
    owner_id: Optional[int] = None,
    owner_type: Optional[str] = None,
    team_id: Optional[int] = None,
) -> Optional[Device]:
    """
    Get a device by DEV EUI with optional owner filtering

    If owner_id is provided with owner_type=USER, filter by user ownership
    If team_id is provided, filter by team ownership
    """
    query = db.query(Device).filter(Device.dev_eui == dev_eui)

    # check if there are any devices returned, if not try lowercase dev_eui
    if not query.first():
        query = db.query(Device).filter(Device.dev_eui == dev_eui.lower())

    # Filter by owner if owner parameters are provided
    if owner_id is not None and owner_type == OwnerType.USER:
        query = query.filter(
            Device.owner_id == owner_id, Device.owner_type == OwnerType.USER
        )
    elif team_id is not None:
        query = query.filter(
            Device.owner_id == team_id, Device.owner_type == OwnerType.TEAM
        )

    device = query.first()
    if device:
        # Manually set label_ids for the response
        setattr(device, "label_ids", [label.id for label in device.labels])

    return device


def get_devices(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    owner_id: Optional[int] = None,
    owner_type: Optional[str] = None,
    team_id: Optional[int] = None,
) -> List[Device]:
    """
    Get all devices with optional owner filtering

    If owner_id is provided with owner_type=USER, filter by user ownership
    If team_id is provided, filter by team ownership
    If owner_id is provided with owner_type=None, get both user owned and team owned devices where user is a member
    """
    query = db.query(Device)

    # Filter by owner if owner parameters are provided
    if owner_id is not None and owner_type == OwnerType.USER:
        query = query.filter(
            Device.owner_id == owner_id, Device.owner_type == OwnerType.USER
        )
    elif team_id is not None:
        query = query.filter(
            Device.owner_id == team_id, Device.owner_type == OwnerType.TEAM
        )
    elif owner_id is not None and not owner_type:
        # Get user's devices and team devices where user is a member
        user_teams = db.query(Team).filter(Team.users.any(id=owner_id)).all()
        team_ids = [team.id for team in user_teams]

        # Union of user's devices and team devices
        if team_ids:
            query = query.filter(
                ((Device.owner_id == owner_id) & (Device.owner_type == OwnerType.USER))
                | (
                    (Device.owner_id.in_(team_ids))
                    & (Device.owner_type == OwnerType.TEAM)
                )
            )
        else:
            query = query.filter(
                Device.owner_id == owner_id, Device.owner_type == OwnerType.USER
            )

    devices = query.offset(skip).limit(limit).all()
    # Set label_ids for each device
    for device in devices:
        setattr(device, "label_ids", [label.id for label in device.labels])

    return devices


def create_device(
    db: Session,
    device: DeviceCreate,
    owner_id: Optional[int] = None,
    owner_type: Optional[str] = OwnerType.USER,
    team_id: Optional[int] = None,
) -> Device:
    """
    Create a new device with optional owner assignment

    If owner_id is provided with owner_type=USER, assign user ownership
    If team_id is provided, assign team ownership
    """
    # Extract label IDs from the request
    label_ids = device.label_ids or []

    # Create a copy of the data excluding label_ids
    device_data = device.dict(exclude={"label_ids"})

    # uppercase the dev_eui
    device_data["dev_eui"] = device_data["dev_eui"].upper()

    # Create the device
    db_device = Device(**device_data)

    # Assign owner based on parameters
    if owner_id is not None and owner_type == OwnerType.USER:
        db_device.owner_id = owner_id
        db_device.owner_type = OwnerType.USER
    elif team_id is not None:
        db_device.owner_id = team_id
        db_device.owner_type = OwnerType.TEAM

    # Add labels if provided
    if label_ids:
        labels = db.query(Label).filter(Label.id.in_(label_ids)).all()
        db_device.labels = labels

    db.add(db_device)
    db.commit()
    db.refresh(db_device)

    # run the device provider hook
    create_device_provider_hook(db, db_device)

    # Set label_ids for the response
    setattr(db_device, "label_ids", [label.id for label in db_device.labels])

    return db_device


def update_device(db: Session, db_device: Device, device: DeviceUpdate) -> Device:

    # Convert device to dictionary, excluding None values
    update_data = device.dict(exclude_unset=True)

    # Extract label_ids if provided
    label_ids = update_data.pop("label_ids", None)

    # Update device attributes
    for field, value in update_data.items():
        setattr(db_device, field, value)

    # Update labels if provided
    if label_ids is not None:
        labels = db.query(Label).filter(Label.id.in_(label_ids)).all()
        db_device.labels = labels

    # Ensure dev_eui is uppercase
    if "dev_eui" in update_data:
        db_device.dev_eui = db_device.dev_eui.upper()

    # Save changes to the database
    db.add(db_device)
    db.commit()
    db.refresh(db_device)

    # Set label_ids for the response
    setattr(db_device, "label_ids", [label.id for label in db_device.labels])

    return db_device


def delete_device(db: Session, db_device: Device) -> Device:
    # first, delete the device from chirpstack
    try:
        # Check if the device is in ChirpStack
        chirpstack_device = chirpstack.get_device(
            dev_eui=db_device.dev_eui, region=db_device.region
        )
        if chirpstack_device:
            # Delete the device from ChirpStack
            chirpstack.delete_device(dev_eui=db_device.dev_eui, region=db_device.region)
    except Exception as e:
        # Log the error
        print(f"Error deleting device from ChirpStack: {e}")

    # Delete the device from the database
    db.delete(db_device)
    db.commit()
    return db_device


def update_device_status(db: Session, device_id: int, status: str) -> bool:
    """
    Update only the status field of a device, avoiding any issues with other fields.

    Args:
        db: The database session
        device_id: The ID of the device to update
        status: The new status value

    Returns:
        bool: True if successful, False otherwise
    """
    try:

        # Fetch the current status of the device
        db_device = get_device(db, device_id)
        if not db_device:
            return False

        current_status = db_device.status
        new_status = status

        # update the device status
        db_device.status = new_status
        db.add(db_device)
        db.commit()

        # create a history entry for the status change
        latest_history = (
            db.query(DeviceHistory)
            .filter(DeviceHistory.device_id == device_id)
            .order_by(DeviceHistory.timestamp.desc())
            .first()
        )

        timestamp = datetime.utcnow()
        if latest_history:
            timestamp = latest_history.timestamp

        # convert time to a string
        timestamp_str = timestamp.strftime("%Y-%m-%d %H:%M:%S")

        db_history = DeviceHistory(
            device_id=device_id,
            event="status_change",
            data={
                "status": new_status,
                "previous_status": current_status,
                "msg": "Device status changed to " + new_status,
                "last_transmission": timestamp_str,
            },
            timestamp=datetime.utcnow(),
        )
        db.add(db_history)
        db.commit()
        db.refresh(db_history)

        return True
    except Exception as e:
        # Log the error
        print(f"Error updating device status: {e}")
        return False


def create_device_provider_hook(db: Session, db_device: Device) -> bool:
    """
    Create a device provider hook for the device.
    This is a placeholder function and should be implemented based on the specific requirements of the device provider.
    """
    if db_device.owner_type == OwnerType.USER:
        providers = get_providers(
            db=db,
            owner_id=db_device.owner_id,
            provider_type="chirpstack",
            is_active=True,
        )
    else:
        # Look for ChirpStack provider based on device ownership
        providers = get_providers(
            db=db,
            team_id=db_device.owner_id,
            provider_type="chirpstack",
            is_active=True,
        )

    if not providers:
        print(
            "No active ChirpStack provider found, skipping chripstack device creation"
        )
        return False

    provider = providers[0]  # Use the first active provider
    provider_config = provider.config

    # Select appropriate device profile based on region and class
    device_profile_id = None
    if db_device.is_class_c:
        # For Class C devices
        if db_device.region == "EU868":
            device_profile_id = provider_config.get(
                "CHIRPSTACK_API_DEVICE_PROFILE_EU868_CLASS_C_ID"
            )
        elif db_device.region == "US915":
            device_profile_id = provider_config.get(
                "CHIRPSTACK_API_DEVICE_PROFILE_US915_CLASS_C_ID"
            )
        elif db_device.region == "AU915":
            device_profile_id = provider_config.get(
                "CHIRPSTACK_API_DEVICE_PROFILE_AU915_CLASS_C_ID"
            )
    else:
        # For standard (Class A) devices
        if db_device.region == "EU868":
            device_profile_id = provider_config.get(
                "CHIRPSTACK_API_DEVICE_PROFILE_EU868_ID"
            )
        elif db_device.region == "US915":
            device_profile_id = provider_config.get(
                "CHIRPSTACK_API_DEVICE_PROFILE_US915_ID"
            )
        elif db_device.region == "AU915":
            device_profile_id = provider_config.get(
                "CHIRPSTACK_API_DEVICE_PROFILE_AU915_ID"
            )

    if not device_profile_id:
        raise ValueError(
            f"No device profile found for region {db_device.region} and class_c={db_device.is_class_c}"
        )

    # Create a ChirpStack client with provider config
    client = chirpstack.get_chirpstack_client(
        server=provider_config.get("CHIRPSTACK_API_SERVER"),
        port=provider_config.get("CHIRPSTACK_API_PORT"),
        tls_enabled=provider_config.get("CHIRPSTACK_API_TLS_ENABLED", False),
        token=provider_config.get("CHIRPSTACK_API_TOKEN"),
    )

    # Create a ChirpStack device
    chirpstack_device = ChirpStackDeviceCreate(
        name=db_device.name,
        dev_eui=db_device.dev_eui,
        app_eui=db_device.app_eui,
        skip_fcnt_check=False,
        is_active=True,
        tags={},
        description=db_device.name,
        device_profile_id=device_profile_id,
        application_id=provider_config.get("CHIRPSTACK_API_APPLICATION_ID"),
    )

    # Create device keys
    device_keys = DeviceKeys(
        appKey=db_device.app_key,
        nwkKey=db_device.app_key,
    )

    try:
        # create the device in chirpstack
        chirpstack_result = chirpstack.create_device(
            device_data=chirpstack_device, region=db_device.region, client=client
        )
        if not chirpstack_result:
            raise ValueError("Failed to create device in ChirpStack")

        # create the device keys in chirpstack
        chirpstack.create_device_keys(
            dev_eui=db_device.dev_eui, device_keys=device_keys, client=client
        )

        return True
    except Exception as e:
        # If ChirpStack creation fails, delete the local device and raise the error
        db.delete(db_device)
        db.commit()
        raise ValueError(f"Failed to create device in ChirpStack: {str(e)}")
