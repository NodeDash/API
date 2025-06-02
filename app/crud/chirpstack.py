"""
CRUD operations for ChirpStack devices.
"""

from typing import Dict, List, Optional, Any, Tuple
from sqlalchemy.orm import Session
from app.core.config import settings

from app.services.integrations.chirpstack_client import ChirpStackClient
from app.schemas.chirpstack import (
    DeviceCreate,
    DeviceUpdate,
    DeviceKeys,
    DeviceActivation,
    DeviceListItem,
    DeviceListResponse,
    DeviceDownlink,
    ApplicationCreate,
    ApplicationUpdate,
    ApplicationListResponse,
    ApplicationListItem,
    HTTPIntegrationCreate,
    HTTPIntegrationUpdate,
    ChirpStackDeviceCreate,
)
import os
from app.models.provider import Provider


def get_chirpstack_client(
    server: Optional[str] = None,
    port: Optional[int] = None,
    tls_enabled: Optional[bool] = None,
    token: Optional[str] = None,
) -> ChirpStackClient:
    """Get a ChirpStack API client."""
    return ChirpStackClient(
        server=server,
        port=port,
        tls_enabled=tls_enabled,
        token=token,
    )


def create_device(
    device_data: ChirpStackDeviceCreate,
    region: str,
    client: Optional[ChirpStackClient] = None,
) -> Dict[str, Any]:
    """
    Create a device in ChirpStack.

    Args:
        device_data: Device data for creation (can be DeviceCreate or ChirpStackDeviceCreate)
        region: Device region (EU868, US915, etc.)
        client: Optional pre-configured ChirpStack client

    Returns:
        Dict containing the created device information
    """
    # Create a ChirpStack client if one wasn't provided
    client = client or get_chirpstack_client()

    # Create device in ChirpStack
    chirpstack_device = client.create_device(device_data=device_data, region=region)
    return chirpstack_device is not None


def create_device_keys(
    dev_eui: str,
    device_keys: DeviceKeys,
    client: Optional[ChirpStackClient] = None,
) -> bool:
    """
    Create device keys in ChirpStack.

    Args:
        dev_eui: Device EUI
        device_keys: Device keys to create
    Returns:
        bool: True if successful
    """
    client = get_chirpstack_client() if client is None else client
    return client.create_device_keys(
        dev_eui=dev_eui,
        device_keys=device_keys,
    )


def get_device(
    dev_eui: str, client: Optional[ChirpStackClient] = None
) -> Dict[str, Any]:
    """
    Get a device from ChirpStack.

    Args:
        dev_eui: Device EUI
        client: Optional pre-configured ChirpStack client

    Returns:
        Dict containing device information
    """
    client = client or get_chirpstack_client()
    return client.get_device(dev_eui=dev_eui)


def update_device(
    db: Session,
    dev_eui: str,
    device_data: DeviceUpdate,
    sync_to_db: bool = True,
    client: Optional[ChirpStackClient] = None,
) -> Dict[str, Any]:
    """
    Update a device in ChirpStack.

    Args:
        db: Database session
        dev_eui: Device EUI
        device_data: Device data for update
        sync_to_db: Whether to update the corresponding device in the local database
        client: Optional pre-configured ChirpStack client

    Returns:
        Dict containing the updated device information
    """
    client = client or get_chirpstack_client()

    # Update device in ChirpStack
    updated_device = client.update_device(
        dev_eui=dev_eui,
        device_data=device_data,
    )

    return updated_device


def delete_device(
    db: Session,
    dev_eui: str,
    sync_to_db: bool = True,
    client: Optional[ChirpStackClient] = None,
) -> bool:
    """
    Delete a device from ChirpStack.

    Args:
        db: Database session
        dev_eui: Device EUI
        sync_to_db: Whether to delete the corresponding device in the local database
        client: Optional pre-configured ChirpStack client

    Returns:
        True if successful
    """
    client = client or get_chirpstack_client()

    # Delete from ChirpStack
    result = client.delete_device(dev_eui=dev_eui)

    return result


def activate_device(
    dev_eui: str,
    activation_data: DeviceActivation,
    client: Optional[ChirpStackClient] = None,
) -> Dict[str, Any]:
    """
    Activate a device in ChirpStack (ABP).

    Args:
        dev_eui: Device EUI
        activation_data: Device activation data
        client: Optional pre-configured ChirpStack client

    Returns:
        Dict containing activation information
    """
    client = client or get_chirpstack_client()
    return client.activate_device(
        dev_eui=dev_eui,
        activation_data=activation_data,
    )


def list_devices(
    application_id: Optional[str] = None,
    limit: int = 10,
    offset: int = 0,
    client: Optional[ChirpStackClient] = None,
) -> DeviceListResponse:
    """
    List devices in ChirpStack.

    Args:
        application_id: Optional application ID to filter
        limit: Max number of devices to return
        offset: Offset for pagination
        client: Optional pre-configured ChirpStack client

    Returns:
        DeviceListResponse with total_count and devices
    """
    client = client or get_chirpstack_client()
    devices, total_count = client.list_devices(
        application_id=application_id,
        limit=limit,
        offset=offset,
    )

    device_list = []
    for device_dict in devices:
        device_list.append(
            DeviceListItem(
                dev_eui=device_dict.get("dev_eui", ""),
                name=device_dict.get("name", ""),
                description=device_dict.get("description", ""),
                application_id=device_dict.get("application_id", ""),
                device_profile_id=device_dict.get("device_profile_id", ""),
                is_disabled=device_dict.get("is_disabled", False),
            )
        )

    return DeviceListResponse(
        total_count=total_count,
        devices=device_list,
    )


def enqueue_downlink(
    dev_eui: str,
    downlink_data: DeviceDownlink,
    client: Optional[ChirpStackClient] = None,
) -> str:
    """
    Enqueue a downlink message for a device.

    Args:
        dev_eui: Device EUI
        downlink_data: Downlink data to enqueue
        client: Optional pre-configured ChirpStack client

    Returns:
        ID of the enqueued downlink
    """
    client = client or get_chirpstack_client()
    return client.enqueue_downlink(
        dev_eui=dev_eui,
        downlink_data=downlink_data,
    )


def get_device_queue(
    dev_eui: str,
    client: Optional[ChirpStackClient] = None,
) -> List[Dict[str, Any]]:
    """
    Get the device's downlink queue.

    Args:
        dev_eui: Device EUI
        client: Optional pre-configured ChirpStack client

    Returns:
        List of queued downlink items
    """
    client = client or get_chirpstack_client()
    return client.get_device_queue(dev_eui=dev_eui)


def flush_device_queue(
    dev_eui: str,
    client: Optional[ChirpStackClient] = None,
) -> Dict[str, bool]:
    """
    Flush all pending downlink messages from the device queue.

    Args:
        dev_eui: Device EUI
        client: Optional pre-configured ChirpStack client

    Returns:
        Dict with success status
    """
    client = client or get_chirpstack_client()
    return client.flush_device_queue(dev_eui=dev_eui)


# Application management functions
def create_application(
    application_data: ApplicationCreate,
    client: Optional[ChirpStackClient] = None,
) -> Dict[str, Any]:
    """
    Create an application in ChirpStack.

    Args:
        application_data: Application data for creation
        client: Optional pre-configured ChirpStack client

    Returns:
        Dict containing the created application information
    """
    client = client or get_chirpstack_client()
    return client.create_application(application_data)


def get_application(
    application_id: str,
    client: Optional[ChirpStackClient] = None,
) -> Dict[str, Any]:
    """
    Get an application from ChirpStack.

    Args:
        application_id: Application ID
        client: Optional pre-configured ChirpStack client

    Returns:
        Dict containing application information
    """
    client = client or get_chirpstack_client()
    return client.get_application(application_id)


def update_application(
    application_id: str,
    application_data: ApplicationUpdate,
    client: Optional[ChirpStackClient] = None,
) -> Dict[str, Any]:
    """
    Update an application in ChirpStack.

    Args:
        application_id: Application ID
        application_data: Application data for update
        client: Optional pre-configured ChirpStack client

    Returns:
        Dict containing the updated application information
    """
    client = client or get_chirpstack_client()
    return client.update_application(application_id, application_data)


def delete_application(
    application_id: str,
    client: Optional[ChirpStackClient] = None,
) -> bool:
    """
    Delete an application from ChirpStack.

    Args:
        application_id: Application ID
        client: Optional pre-configured ChirpStack client

    Returns:
        True if successful
    """
    client = client or get_chirpstack_client()
    return client.delete_application(application_id)


def list_applications(
    limit: int = 10,
    offset: int = 0,
    client: Optional[ChirpStackClient] = None,
) -> ApplicationListResponse:
    """
    List applications in ChirpStack.

    Args:
        limit: Max number of applications to return
        offset: Offset for pagination
        client: Optional pre-configured ChirpStack client

    Returns:
        ApplicationListResponse with total_count and applications
    """
    client = client or get_chirpstack_client()
    applications, total_count = client.list_applications(
        limit=limit,
        offset=offset,
    )

    application_list = []
    for app_dict in applications:
        application_list.append(
            ApplicationListItem(
                id=app_dict.get("id", ""),
                name=app_dict.get("name", ""),
                description=app_dict.get("description", ""),
            )
        )

    return ApplicationListResponse(
        total_count=total_count,
        applications=application_list,
    )


def get_application_by_id(
    application_id: str,
    client: Optional[ChirpStackClient] = None,
) -> Dict[str, Any]:
    """
    Get an application by ID from ChirpStack.
    Args:
        application_id: Application ID
        client: Optional pre-configured ChirpStack client
    Returns:
        Dict containing application information
    """
    client = client or get_chirpstack_client()
    return client.get_application_by_id(application_id)


def create_device_profile(
    device_profile_data: Dict[str, Any],
    client: Optional[ChirpStackClient] = None,
) -> Dict[str, Any]:
    """
    Create a device profile in ChirpStack.
    Args:
        device_profile_data: Device profile data for creation
        client: Optional pre-configured ChirpStack client
    Returns:
        Dict containing the created device profile information
    """
    client = client or get_chirpstack_client()
    return client.create_device_profile(device_profile_data)


# HTTP Integration management functions
def create_http_integration(
    integration_data: HTTPIntegrationCreate,
    client: Optional[ChirpStackClient] = None,
) -> Dict[str, Any]:
    """
    Create an HTTP integration for an application in ChirpStack.

    Args:
        integration_data: HTTP integration data for creation
        client: Optional pre-configured ChirpStack client

    Returns:
        Dict containing creation status
    """
    client = client or get_chirpstack_client()
    return client.create_http_integration(integration_data)


def get_http_integration(
    application_id: str,
    client: Optional[ChirpStackClient] = None,
) -> Dict[str, Any]:
    """
    Get the HTTP integration for an application from ChirpStack.

    Args:
        application_id: Application ID
        client: Optional pre-configured ChirpStack client

    Returns:
        Dict containing HTTP integration information
    """
    client = client or get_chirpstack_client()
    return client.get_http_integration(application_id)


def get_applications(
    client: Optional[ChirpStackClient] = None,
) -> List[Dict[str, Any]]:
    """
    Get all applications from ChirpStack.

    Args:
        client: Optional pre-configured ChirpStack client

    Returns:
        List of applications
    """
    client = client or get_chirpstack_client()
    return client.get_applications()


def update_http_integration(
    application_id: str,
    integration_data: HTTPIntegrationUpdate,
    client: Optional[ChirpStackClient] = None,
) -> Dict[str, Any]:
    """
    Update an HTTP integration in ChirpStack.

    Args:
        application_id: Application ID
        integration_data: HTTP integration data for update
        client: Optional pre-configured ChirpStack client

    Returns:
        Dict containing the updated HTTP integration information
    """
    client = client or get_chirpstack_client()
    return client.update_http_integration(application_id, integration_data)


def delete_http_integration(
    application_id: str,
    client: Optional[ChirpStackClient] = None,
) -> bool:
    """
    Delete an HTTP integration from ChirpStack.

    Args:
        application_id: Application ID
        client: Optional pre-configured ChirpStack client

    Returns:
        True if successful
    """
    client = client or get_chirpstack_client()
    return client.delete_http_integration(application_id)


def run_setup(
    db: Session,
    provider: Provider,
) -> bool:
    """
    Run setup for ChirpStack integration.

    This function sets up a ChirpStack integration with:
    1. Application creation/verification
    2. HTTP integration setup
    3. Device profiles for multiple regions with standard and Class C variants

    Args:
        db: Database session
        provider: Provider model with ChirpStack configuration

    Returns:
        bool: True if setup was successful
    """
    print("ChirpStack setup: Starting setup process...")
    json_config = provider.config

    # Validate required configuration
    api_server = json_config.get("CHIRPSTACK_API_SERVER")
    api_port = json_config.get("CHIRPSTACK_API_PORT")
    api_tls_enabled = json_config.get("CHIRPSTACK_API_TLS_ENABLED")
    api_token = json_config.get("CHIRPSTACK_API_TOKEN")

    if not api_server or not api_port or not api_token:
        raise ValueError("Missing required configuration for ChirpStack")

    # Type checking for configuration values
    if not isinstance(api_tls_enabled, bool):
        api_tls_enabled = str(api_tls_enabled).lower() == "true"
        json_config["CHIRPSTACK_API_TLS_ENABLED"] = api_tls_enabled
        print(f"ChirpStack setup: Converted TLS enabled to boolean: {api_tls_enabled}")

    if not isinstance(api_port, int):
        try:
            api_port = int(api_port)
            json_config["CHIRPSTACK_API_PORT"] = api_port
            print(f"ChirpStack setup: Converted port to integer: {api_port}")
        except (ValueError, TypeError):
            raise ValueError("CHIRPSTACK_API_PORT must be an integer")

    if not isinstance(api_server, str):
        raise ValueError("CHIRPSTACK_API_SERVER must be a string")

    if not isinstance(api_token, str):
        raise ValueError("CHIRPSTACK_API_TOKEN must be a string")

    # Create a ChirpStack client
    print(f"ChirpStack setup: Creating client for {api_server}:{api_port}")
    client = get_chirpstack_client(
        server=api_server,
        port=api_port,
        tls_enabled=api_tls_enabled,
        token=api_token,
    )

    # Test connection to the ChirpStack server
    try:
        print("ChirpStack setup: Testing connection to server...")
        client.get_adr_algorithms()
        print("ChirpStack setup: Successfully connected to ChirpStack server")
    except Exception as e:
        print(f"ChirpStack setup: Connection error: {str(e)}")
        raise ValueError(f"Failed to connect to ChirpStack server: {str(e)}")

    # Step 1: Set up or verify the application
    application_id = json_config.get("CHIRPSTACK_API_APPLICATION_ID")
    application = None

    tenantId = json_config.get("CHIRPSTACK_API_TENANT_ID")

    if not tenantId:
        raise ValueError("CHIRPSTACK_API_TENANT_ID must be provided")

    print(f"ChirpStack setup: Checking for application ID in config: {application_id}")

    if application_id:
        # Check if the application exists in ChirpStack
        try:
            print(f"ChirpStack setup: Verifying application with ID: {application_id}")
            application = client.get_application_by_id(
                application_id, tenantId=tenantId
            )
            if application:
                print(
                    f"ChirpStack setup: Found existing application: {application.get('name', 'Unknown')}"
                )
            else:
                print(
                    f"ChirpStack setup: Application ID {application_id} not found in ChirpStack"
                )
                application_id = None  # Reset to None to create a new one
        except Exception as e:
            print(f"ChirpStack setup: Error verifying application: {str(e)}")
            application_id = None  # Reset to None to create a new one

    if not application_id:
        # Create a new application
        try:
            print("ChirpStack setup: Creating new application 'NodeDash'")
            application_data = ApplicationCreate(
                name="NodeDash",
                description="NodeDash Application",
                tenantId=tenantId,
            )
            application = create_application(application_data, client)
            application_id = application.get("id")

            if not application_id:
                raise ValueError(
                    "Failed to create ChirpStack application: No ID returned"
                )

            print(
                f"ChirpStack setup: Created new application with ID: {application_id}"
            )

            # Update the provider config with the new application_id
            json_config["CHIRPSTACK_API_APPLICATION_ID"] = application_id
        except Exception as e:
            print(f"ChirpStack setup: Error creating application: {str(e)}")
            raise ValueError(f"Failed to create ChirpStack application: {str(e)}")

    # Step 2: Set up or verify HTTP integration
    try:
        print(
            f"ChirpStack setup: Checking for HTTP integration for application {application_id}"
        )
        http_integration = client.get_http_integration(application_id)

        if http_integration:
            print("ChirpStack setup: Found existing HTTP integration")
            # Verify webhook URL and API key
            webhook_url = json_config.get("CHIRPSTACK_WEBHOOK_URL")
            webhook_token = json_config.get("X-API-KEY")

            if (
                webhook_url
                and webhook_token
                and (
                    http_integration.get("eventEndpointUrl") != webhook_url
                    or http_integration.get("headers", {}).get("X-API-KEY")
                    != webhook_token
                )
            ):
                # Update integration if URL or token has changed
                print(
                    "ChirpStack setup: Updating HTTP integration with current webhook URL and API key"
                )
                http_integration_update = HTTPIntegrationUpdate(
                    endpoint=webhook_url,
                    headers={"X-API-KEY": webhook_token},
                    event_endpoints={
                        "uplink": True,
                        "join": True,
                        "status": True,
                        "ack": True,
                        "error": True,
                    },
                )
                client.update_http_integration(application_id, http_integration_update)
        else:
            # Create a new HTTP integration
            print("ChirpStack setup: No HTTP integration found, creating new one")
            # Get the webhook URL and token from environment variables or config
            webhook_url = settings.INGEST_ADDRESS + "/api/v1/ingest/chirpstack"
            webhook_token = json_config.get("X-API-KEY", "")

            # If there isn't a token, create one
            if not webhook_token:
                import uuid

                webhook_token = str(uuid.uuid4())
                json_config["X-API-KEY"] = webhook_token
                print(f"ChirpStack setup: Generated new API key: {webhook_token}")

            # Create the HTTP integration
            http_integration_data = HTTPIntegrationCreate(
                application_id=application_id,
                endpoint=webhook_url,
                headers={"X-API-KEY": webhook_token},
                event_endpoints={
                    "uplink": True,
                    "join": True,
                    "status": True,
                    "ack": True,
                    "error": True,
                },
            )

            create_http_integration(http_integration_data, client)
            print(
                f"ChirpStack setup: Created HTTP integration with webhook URL: {webhook_url}"
            )

    except Exception as e:
        print(f"ChirpStack setup: Error with HTTP integration: {str(e)}")
        # Don't raise error here, as device profiles are still needed

    # Step 3: Set up device profiles
    print("ChirpStack setup: Setting up device profiles...")
    json_config = setup_device_profiles(client, json_config)

    print("JSON_CONFIG: ", json_config)

    # Update provider with the modified config - Create a new dict to ensure SQLAlchemy detects the change
    from sqlalchemy.orm.attributes import flag_modified

    # Create a new copy of the config to ensure the change is detected
    provider.config = dict(json_config)

    # Explicitly mark the config field as modified
    flag_modified(provider, "config")

    db.commit()
    print("ChirpStack setup: Setup completed successfully")

    return True


# Check if the device profile exists
def setup_device_profiles(client, json_config):
    """
    Set up device profiles for multiple regions (EU868, US915, AU915) including Class C variants.
    First checks if profile IDs exist in json_config, then fetches them from ChirpStack if needed,
    or creates new ones if they don't exist.

    Args:
        client: ChirpStack client
        json_config: Provider configuration dictionary

    Returns:
        dict: Updated json_config with device profile IDs
    """
    # Define the regions and their configurations
    regions = {
        "EU868": {
            "standard_key": "CHIRPSTACK_API_DEVICE_PROFILE_EU868_ID",
            "class_c_key": "CHIRPSTACK_API_DEVICE_PROFILE_EU868_CLASS_C_ID",
            "region_name": "EU868",
            "reg_params_revision": "A",
        },
        "US915": {
            "standard_key": "CHIRPSTACK_API_DEVICE_PROFILE_US915_ID",
            "class_c_key": "CHIRPSTACK_API_DEVICE_PROFILE_US915_CLASS_C_ID",
            "region_name": "US915",
            "reg_params_revision": "A",
        },
        "AU915": {
            "standard_key": "CHIRPSTACK_API_DEVICE_PROFILE_AU915_ID",
            "class_c_key": "CHIRPSTACK_API_DEVICE_PROFILE_AU915_CLASS_C_ID",
            "region_name": "AU915",
            "reg_params_revision": "A",
        },
    }

    for region, config in regions.items():
        # Set up standard profile (Class A)
        standard_profile_id = json_config.get(config["standard_key"])
        standard_profile_name = f"NodeDash - {region}"

        print(f"Setup: Processing standard profile for {region}")
        print(f"Setup: Config has profile ID: {standard_profile_id}")

        # Check if standard profile ID exists in config
        if not standard_profile_id:
            # Profile doesn't exist, create a new one
            standard_profile_data = {
                "allowRoaming": True,
                "region": region,
                "regionConfigId": region,
                "supportsClassB": False,
                "supportsClassC": False,
                "supportsOtaa": True,
                "tags": {},
                "name": standard_profile_name,
                "description": f"Standard device profile for {region} region",
                "mac_version": "LORAWAN_1_0_3",
                "reg_params_revision": config["reg_params_revision"],
                "tenantId": json_config.get("CHIRPSTACK_API_TENANT_ID"),
            }

            try:
                print(f"Setup: Creating new standard profile for {region}...")
                standard_profile = client.create_device_profile(standard_profile_data)
                standard_profile_id = standard_profile.get("id")
                if standard_profile_id:
                    json_config[config["standard_key"]] = standard_profile_id
                    print(
                        f"Setup: Created new standard profile for {region}: {standard_profile_id}"
                    )
                else:
                    print(
                        f"Setup: Failed to create standard profile for {region} - no ID returned"
                    )
            except Exception as e:
                print(f"Setup: Error creating standard profile for {region}: {str(e)}")

        # Set up Class C profile
        class_c_profile_id = json_config.get(config["class_c_key"])
        class_c_profile_name = f"NodeDash - {region} - Class C"

        print(f"Setup: Processing Class C profile for {region}")
        print(f"Setup: Config has Class C profile ID: {class_c_profile_id}")

        # Check if class C profile ID exists in config
        if not class_c_profile_id:
            # Profile doesn't exist, create a new one
            class_c_profile_data = {
                "name": class_c_profile_name,
                "description": f"Class C device profile for {region} region",
                "mac_version": "LORAWAN_1_0_3",
                "reg_params_revision": config["reg_params_revision"],
                "allowRoaming": True,
                "region": region,
                "regionConfigId": region,
                "supportsClassB": False,
                "supportsClassC": True,
                "supportsOtaa": True,
                "tags": {},
                "tenantId": json_config.get("CHIRPSTACK_API_TENANT_ID"),
            }

            try:
                print(f"Setup: Creating new Class C profile for {region}...")
                class_c_profile = client.create_device_profile(class_c_profile_data)
                class_c_profile_id = class_c_profile.get("id")
                if class_c_profile_id:
                    json_config[config["class_c_key"]] = class_c_profile_id
                    print(
                        f"Setup: Created new Class C profile for {region}: {class_c_profile_id}"
                    )
                else:
                    print(
                        f"Setup: Failed to create Class C profile for {region} - no ID returned"
                    )
            except Exception as e:
                print(f"Setup: Error creating Class C profile for {region}: {str(e)}")

    return json_config
