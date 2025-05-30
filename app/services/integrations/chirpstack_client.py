"""
ChirpStack API client for interacting with the ChirpStack REST API.
"""

import os
import json
import requests
import base64
from typing import Dict, List, Optional, Any, Tuple


from app.schemas.chirpstack import (
    DeviceUpdate,
    DeviceActivation,
    DeviceDownlink,
    ApplicationCreate,
    ApplicationUpdate,
    DeviceKeys,
    HTTPIntegrationCreate,
    HTTPIntegrationUpdate,
    ChirpStackDeviceCreate,
)


class ChirpStackClient:
    """Client for interacting with the ChirpStack REST API."""

    def __init__(
        self,
        server: Optional[str] = None,
        port: Optional[int] = None,
        tls_enabled: Optional[bool] = None,
        token: Optional[str] = None,
    ):
        """Initialize ChirpStack API client.

        Args:
            server: ChirpStack API server address
            port: ChirpStack API server port
            tls_enabled: Whether to use TLS for connection
            token: ChirpStack API token
        """
        self.server = server or os.getenv("CHIRPSTACK_API_SERVER", "localhost")
        self.port = port or os.getenv("CHIRPSTACK_API_PORT", 80)
        self.tls_enabled = tls_enabled or os.getenv("CHIRPSTACK_API_TLS_ENABLED", True)
        self.token = token or os.getenv("CHIRPSTACK_API_TOKEN", " ")
        self.application_id = os.getenv("CHIRPSTACK_API_APPLICATION_ID", "")
        self.device_profile_id = os.getenv("CHIRPSTACK_API_DEVICE_PROFILE_ID", "")

        if not self.server or not self.port:
            raise ValueError("ChirpStack API server and port must be configured")

        # Set up the base URL for API requests
        protocol = "https" if self.tls_enabled else "http"
        self.base_url = f"{protocol}://{self.server}:{self.port}"

        # Set up request headers with authentication
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        if self.token:
            # ChirpStack API requires the 'Bearer' prefix for the token
            self.headers["Grpc-Metadata-Authorization"] = f"Bearer {self.token}"

    def _make_request(
        self, method: str, endpoint: str, data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Make a REST API request to ChirpStack.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint path
            data: Optional data to send with request

        Returns:
            Response data as dict
        """
        url = f"{self.base_url}{endpoint}"

        try:
            if method == "GET":
                response = requests.get(url, headers=self.headers)
            elif method == "POST":
                # Ensure proper JSON serialization with correct boolean formatting
                if data:
                    headers = self.headers.copy()
                    json_string = json.dumps(data, ensure_ascii=False)
                    # Debug: Show the actual JSON string being sent (with double quotes)
                    print(f"DEBUG - Sending JSON to API: {json_string}")
                    response = requests.post(
                        url,
                        headers=headers,
                        data=json_string,
                    )
                else:
                    response = requests.post(url, headers=self.headers)
            elif method == "PUT":
                # Ensure proper JSON serialization with correct boolean formatting
                if data:
                    headers = self.headers.copy()
                    json_string = json.dumps(data, ensure_ascii=False)
                    # Debug: Show the actual JSON string being sent (with double quotes)
                    print(f"DEBUG - Sending JSON to API: {json_string}")
                    response = requests.put(
                        url,
                        headers=headers,
                        data=json_string,
                    )
                else:
                    response = requests.put(url, headers=self.headers)
            elif method == "DELETE":
                response = requests.delete(url, headers=self.headers)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            # Check for errors
            response.raise_for_status()

            # Return JSON response if there is content
            if response.text:
                return response.json()
            return {"success": True}

        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code
            try:
                error_detail = e.response.json()
                detail = str(error_detail)
            except json.JSONDecodeError:
                detail = e.response.text or str(e)

            if status_code == 404:
                # Handle 404 errors differently in some cases
                if "GET" in method:
                    return {}

            raise Exception(f"API Error ({status_code}): {detail}")
        except requests.exceptions.RequestException as e:
            raise Exception(f"Request failed: {str(e)}")

    def create_device(self, device_data: ChirpStackDeviceCreate, region: str) -> bool:
        """Create a device in ChirpStack.

        Args:
            device_data: Device data for creation

        Returns:
            Dict containing the created device information
        """

        device = {
            "device": {
                "applicationId": device_data.application_id,
                "description": device_data.description,
                "devEui": device_data.dev_eui.lower(),
                "deviceProfileId": device_data.device_profile_id,
                "isDisabled": not device_data.is_active,
                "joinEui": device_data.app_eui.lower(),
                "name": device_data.name,
                "skipFcntCheck": device_data.skip_fcnt_check,
                "tags": {},
                "variables": {},
            }
        }

        print("Creating device with data:", device)

        # Add tags if provided
        if device_data.tags:
            device["device"]["tags"] = device_data.tags

        self._make_request("POST", "/api/devices", device)
        # Fetch the created device to return complete info
        return self.get_device(device_data.dev_eui)

    def get_adr_algorithms(self) -> List[Dict[str, Any]]:
        """Get all ADR algorithms from ChirpStack.

        Returns:
            List of ADR algorithms
        """
        response = self._make_request("GET", "/api/device-profiles/adr-algorithms")
        if "result" in response:
            return response["result"]
        return []

    def get_applications(self) -> List[Dict[str, Any]]:
        """Get all applications from ChirpStack.

        Returns:
            List of applications
        """
        response = self._make_request("GET", "/api/applications")
        if "result" in response:
            return response["result"]
        return []

    def create_device_keys(
        self, dev_eui: str, device_keys: DeviceKeys
    ) -> Dict[str, Any]:
        """Create device keys in ChirpStack.

        Args:
            dev_eui: Device EUI
            device_keys: Device keys for creation
        Returns:
            Dict containing the created device keys information

        """

        data = {
            "deviceKeys": {
                "appKey": device_keys.appKey,
                "nwkKey": device_keys.nwkKey,
            }
        }

        # Create device keys
        print("Creating device keys with data:", data)

        self._make_request("POST", f"/api/devices/{dev_eui.lower()}/keys", data)

        return True

    def get_device(self, dev_eui: str) -> Dict[str, Any]:
        """Get a device from ChirpStack.

        Args:
            dev_eui: Device EUI

        Returns:
            Dict containing device information
        """
        response = self._make_request("GET", f"/api/devices/{dev_eui.lower()}")
        if "device" in response:
            return response["device"]
        return response

    def update_device(self, dev_eui: str, device_data: DeviceUpdate) -> Dict[str, Any]:
        """Update a device in ChirpStack.

        Args:
            dev_eui: Device EUI
            device_data: Device data for update

        Returns:
            Dict containing the updated device information
        """
        # First get the current device to merge with updates
        current_device = self.get_device(dev_eui)

        # Create update request with changed fields
        device = {
            "device": {
                "devEui": dev_eui.lower(),
                "name": (
                    device_data.name
                    if device_data.name is not None
                    else current_device.get("name", "")
                ),
                "description": (
                    device_data.description
                    if device_data.description is not None
                    else current_device.get("description", "")
                ),
                "applicationId": self.application_id,
                "deviceProfileId": self.device_profile_id,
                "isDisabled": (
                    not device_data.is_active
                    if device_data.is_active is not None
                    else current_device.get("isDisabled", False)
                ),
                "skipFcntCheck": (
                    device_data.skip_fcnt_check
                    if device_data.skip_fcnt_check is not None
                    else current_device.get("skipFcntCheck", False)
                ),
            }
        }

        # Update tags if provided
        if device_data.tags is not None:
            device["device"]["tags"] = device_data.tags
        elif "tags" in current_device:
            device["device"]["tags"] = current_device["tags"]

        self._make_request("PUT", f"/api/devices/{dev_eui.lower()}", device)
        # Fetch the updated device to return complete info
        return self.get_device(dev_eui)

    def delete_device(self, dev_eui: str) -> bool:
        """Delete a device from ChirpStack.

        Args:
            dev_eui: Device EUI

        Returns:
            True if successful, raises exception otherwise
        """
        self._make_request("DELETE", f"/api/devices/{dev_eui.lower()}")
        return True

    def activate_device(
        self, dev_eui: str, activation_data: DeviceActivation
    ) -> Dict[str, Any]:
        """Activate a device in ChirpStack (ABP).

        Args:
            dev_eui: Device EUI
            activation_data: Device activation data

        Returns:
            Dict containing activation information
        """
        data = {
            "deviceActivation": {
                "devEui": dev_eui.lower(),
                "devAddr": activation_data.dev_addr,
                "appSKey": activation_data.app_s_key,
                "nwkSEncKey": activation_data.nwk_s_enc_key,
                "sNwkSIntKey": activation_data.s_nwk_s_int_key,
                "fNwkSIntKey": activation_data.f_nwk_s_int_key,
                "fCntUp": activation_data.fcnt_up,
                "nFCntDown": activation_data.fcnt_down,
            }
        }

        self._make_request("POST", f"/api/devices/{dev_eui.lower()}/activate", data)
        return {"success": True}

    def list_devices(
        self,
        limit: int = 10,
        offset: int = 0,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """List devices in ChirpStack.

        Args:
            application_id: Optional application ID to filter
            limit: Max number of devices to return
            offset: Offset for pagination

        Returns:
            Tuple of (list of devices, total count)
        """
        endpoint = f"/api/devices?applicationId={self.application_id}"
        params = []

        if limit:
            params.append(f"limit={limit}")
        if offset:
            params.append(f"offset={offset}")

        if params:
            endpoint += "?" + "&".join(params)

        response = self._make_request("GET", endpoint)
        result = response.get("result", [])
        total_count = response.get("totalCount", len(result))

        return result, total_count

    def enqueue_downlink(self, dev_eui: str, downlink_data: DeviceDownlink) -> str:
        """Enqueue a downlink message for a device.

        Args:
            dev_eui: Device EUI
            downlink_data: Downlink data to enqueue

        Returns:
            ID of the enqueued downlink
        """
        # Convert hex string to bytes if data is provided as hex
        if isinstance(downlink_data.data, str):
            if downlink_data.data.startswith("0x"):
                # Remove 0x prefix if present
                data_str = downlink_data.data[2:]
            else:
                data_str = downlink_data.data

            # Assuming data is hex encoded
            try:
                # Convert to base64 for REST API
                data_bytes = bytes.fromhex(data_str)
                data_base64 = base64.b64encode(data_bytes).decode("ascii")
            except ValueError:
                # Maybe it's already base64?
                data_base64 = downlink_data.data
        else:
            raise ValueError("Downlink data must be a string")

        # Create queue item
        data = {
            "queueItem": {
                "devEui": dev_eui.lower(),
                "confirmed": downlink_data.confirmed,
                "fPort": downlink_data.f_port,
                "data": data_base64,
            }
        }

        response = self._make_request(
            "POST", f"/api/devices/{dev_eui.lower()}/queue", data
        )
        return response.get("id", "")

    def get_device_queue(self, dev_eui: str) -> List[Dict[str, Any]]:
        """Get the device's downlink queue.

        Args:
            dev_eui: Device EUI

        Returns:
            List of queued downlink items
        """
        response = self._make_request("GET", f"/api/devices/{dev_eui.lower()}/queue")
        return response.get("items", [])

    def flush_device_queue(self, dev_eui: str) -> Dict[str, bool]:
        """Flush all pending downlink messages from the device queue.

        Args:
            dev_eui: Device EUI

        Returns:
            Dict with success status
        """
        self._make_request("DELETE", f"/api/devices/{dev_eui.lower()}/queue")
        return {"success": True}

    def create_application(self, application_data: ApplicationCreate) -> Dict[str, Any]:
        """Create an application in ChirpStack.

        Args:
            application_data: Application data for creation

        Returns:
            Dict containing the created application information
        """
        data = {
            "application": {
                "name": application_data.name,
                "description": application_data.description,
                "tenantId": application_data.tenantId,
            }
        }

        # Add tags if provided
        if application_data.tags:
            data["application"]["tags"] = application_data.tags

        response = self._make_request("POST", "/api/applications", data)

        # Return the application ID
        return {
            "id": response.get("id", ""),
            "name": application_data.name,
        }

    def get_application(self, application_id: str, tenantId: str) -> Dict[str, Any]:
        """Get an application from ChirpStack.

        Args:
            application_id: Application ID

        Returns:
            Dict containing application information
        """
        response = self._make_request(
            "GET", f"/api/applications/{application_id}?tenantId={tenantId}"
        )
        if "application" in response:
            return response["application"]
        return response

    def update_application(
        self, application_id: str, application_data: ApplicationUpdate
    ) -> Dict[str, Any]:
        """Update an application in ChirpStack.

        Args:
            application_id: Application ID
            application_data: Application data for update

        Returns:
            Dict containing the updated application information
        """
        # First get the current application to merge with updates
        current_app = self.get_application(application_id)

        data = {
            "application": {
                "id": application_id,
                "name": (
                    application_data.name
                    if application_data.name is not None
                    else current_app.get("name", "")
                ),
                "description": (
                    application_data.description
                    if application_data.description is not None
                    else current_app.get("description", "")
                ),
            }
        }

        # Update tags if provided
        if application_data.tags is not None:
            data["application"]["tags"] = application_data.tags
        elif "tags" in current_app:
            data["application"]["tags"] = current_app["tags"]

        self._make_request("PUT", f"/api/applications/{application_id}", data)

        # Fetch the updated application to return complete info
        return self.get_application(application_id)

    def delete_application(self, application_id: str) -> bool:
        """Delete an application from ChirpStack.

        Args:
            application_id: Application ID

        Returns:
            True if successful, raises exception otherwise
        """
        self._make_request("DELETE", f"/api/applications/{application_id}")
        return True

    def list_applications(
        self,
        limit: int = 10,
        offset: int = 0,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """List applications in ChirpStack.

        Args:
            limit: Max number of applications to return
            offset: Offset for pagination

        Returns:
            Tuple of (list of applications, total count)
        """
        endpoint = "/api/applications"
        params = []

        if limit:
            params.append(f"limit={limit}")
        if offset:
            params.append(f"offset={offset}")

        if params:
            endpoint += "?" + "&".join(params)

        response = self._make_request("GET", endpoint)
        result = response.get("result", [])
        total_count = response.get("totalCount", len(result))

        return result, total_count

    def create_http_integration(
        self, integration_data: HTTPIntegrationCreate
    ) -> Dict[str, Any]:
        """Create an HTTP integration for an application in ChirpStack.

        Args:
            integration_data: HTTP integration data for creation

        Returns:
            Dict containing creation status
        """
        # Configure the HTTP integration
        integration = {
            "integration": {
                "applicationId": self.application_id,
                "headers": integration_data.headers or {},
                "eventEndpointUrl": integration_data.endpoint,
                "uplinkDataEnabled": False,
                "joinEnabled": False,
                "ackEnabled": False,
                "errorEnabled": False,
                "statusEnabled": False,
                "locationEnabled": False,
                "txAckEnabled": False,
            }
        }

        # Configure event endpoints
        if integration_data.event_endpoints:
            for event, enabled in integration_data.event_endpoints.items():
                if event == "uplink" and enabled:
                    integration["integration"]["uplinkDataEnabled"] = True
                elif event == "join" and enabled:
                    integration["integration"]["joinEnabled"] = True
                elif event == "ack" and enabled:
                    integration["integration"]["ackEnabled"] = True
                elif event == "error" and enabled:
                    integration["integration"]["errorEnabled"] = True
                elif event == "status" and enabled:
                    integration["integration"]["statusEnabled"] = True
                elif event == "location" and enabled:
                    integration["integration"]["locationEnabled"] = True
                elif event == "txack" and enabled:
                    integration["integration"]["txAckEnabled"] = True

        endpoint = (
            f"/api/applications/{integration_data.application_id}/integrations/http"
        )
        self._make_request("POST", endpoint, integration)

        # Return success status
        return {
            "success": True,
            "application_id": integration_data.application_id,
            "endpoint": integration_data.endpoint,
        }

    def get_http_integration(self, application_id: str) -> Dict[str, Any]:
        """Get the HTTP integration for an application from ChirpStack.

        Args:
            application_id: Application ID

        Returns:
            Dict containing HTTP integration information
        """
        endpoint = f"/api/applications/{application_id}/integrations/http"
        try:
            response = self._make_request("GET", endpoint)
            if "integration" in response:
                return response["integration"]
            return response
        except Exception as e:
            if "404" in str(e):
                return {}  # Return empty dict if integration doesn't exist
            raise

    def update_http_integration(
        self, application_id: str, integration_data: HTTPIntegrationUpdate
    ) -> Dict[str, Any]:
        """Update an HTTP integration in ChirpStack.

        Args:
            application_id: Application ID
            integration_data: HTTP integration data for update

        Returns:
            Dict containing the updated HTTP integration information
        """
        # Get current integration to merge with updates
        try:
            current_integration = self.get_http_integration(application_id)
            if not current_integration:
                raise Exception(
                    f"HTTP integration for application {application_id} not found."
                )
        except Exception as e:
            if "404" not in str(e):
                raise
            # If integration doesn't exist, treat this as an error
            raise Exception(
                f"HTTP integration for application {application_id} not found."
            )

        # Configure the HTTP integration with updated values
        integration = {
            "integration": {
                "applicationId": application_id,
                "headers": {},
            }
        }

        # Update endpoint if provided, otherwise keep existing
        if integration_data.endpoint is not None:
            integration["integration"]["eventEndpointUrl"] = integration_data.endpoint
        elif "eventEndpointUrl" in current_integration:
            integration["integration"]["eventEndpointUrl"] = current_integration[
                "eventEndpointUrl"
            ]
        else:
            raise Exception(
                "Endpoint URL must be provided as it doesn't exist in the current integration."
            )

        # Update headers if provided, otherwise keep existing
        if integration_data.headers is not None:
            integration["integration"]["headers"] = integration_data.headers
        elif "headers" in current_integration:
            integration["integration"]["headers"] = current_integration["headers"]

        # Configure event endpoints
        if integration_data.event_endpoints:
            for event, enabled in integration_data.event_endpoints.items():
                if event == "uplink":
                    integration["integration"]["uplinkDataEnabled"] = enabled
                elif event == "join":
                    integration["integration"]["joinEnabled"] = enabled
                elif event == "ack":
                    integration["integration"]["ackEnabled"] = enabled
                elif event == "error":
                    integration["integration"]["errorEnabled"] = enabled
                elif event == "status":
                    integration["integration"]["statusEnabled"] = enabled
                elif event == "location":
                    integration["integration"]["locationEnabled"] = enabled
                elif event == "txack":
                    integration["integration"]["txAckEnabled"] = enabled
        else:
            # Preserve existing event settings
            integration["integration"]["uplinkDataEnabled"] = current_integration.get(
                "uplinkDataEnabled", False
            )
            integration["integration"]["joinEnabled"] = current_integration.get(
                "joinEnabled", False
            )
            integration["integration"]["ackEnabled"] = current_integration.get(
                "ackEnabled", False
            )
            integration["integration"]["errorEnabled"] = current_integration.get(
                "errorEnabled", False
            )
            integration["integration"]["statusEnabled"] = current_integration.get(
                "statusEnabled", False
            )
            integration["integration"]["locationEnabled"] = current_integration.get(
                "locationEnabled", False
            )
            integration["integration"]["txAckEnabled"] = current_integration.get(
                "txAckEnabled", False
            )

        endpoint = f"/api/applications/{application_id}/integrations/http"
        self._make_request("PUT", endpoint, integration)

        # Get updated integration
        return self.get_http_integration(application_id)

    def delete_http_integration(self, application_id: str) -> bool:
        """Delete an HTTP integration from ChirpStack.

        Args:
            application_id: Application ID

        Returns:
            True if successful, raises exception otherwise
        """
        endpoint = f"/api/applications/{application_id}/integrations/http"
        self._make_request("DELETE", endpoint)
        return True

    def list_device_profiles(
        self, limit: int = 100, offset: int = 0
    ) -> Tuple[List[Dict[str, Any]], int]:
        """List device profiles in ChirpStack.

        Args:
            limit: Max number of device profiles to return
            offset: Offset for pagination

        Returns:
            Tuple of (list of device profiles, total count)
        """
        endpoint = "/api/device-profiles"
        params = []

        if limit:
            params.append(f"limit={limit}")
        if offset:
            params.append(f"offset={offset}")

        if params:
            endpoint += "?" + "&".join(params)

        response = self._make_request("GET", endpoint)
        result = response.get("result", [])
        total_count = response.get("totalCount", len(result))

        return result, total_count

    def create_device_profile(
        self, device_profile_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a device profile in ChirpStack.

        Args:
            device_profile_data: Device profile data for creation

        Returns:
            Dict containing the created device profile information
        """
        # Format the device profile data for ChirpStack API
        data = {
            "deviceProfile": {
                "name": device_profile_data.get("name", "New Device Profile"),
                "description": device_profile_data.get("description", ""),
                "supportsClassB": device_profile_data.get("supportsClassB", False),
                "supportsClassC": device_profile_data.get("supportsClassC", False),
                "macVersion": device_profile_data.get("macVersion", "LORAWAN_1_0_3"),
                "regParamsRevision": device_profile_data.get("regParamsRevision", "A"),
                "supportsOtaa": device_profile_data.get("supportsOtaa", True),
                "tags": device_profile_data.get("tags", {}),
                "region": device_profile_data.get("region", ""),
                "regionConfigId": device_profile_data.get("regionConfigId", ""),
                "allowRoaming": device_profile_data.get("allowRoaming", True),
                "tenantId": device_profile_data.get("tenantId", ""),
            }
        }

        print(f"Creating device profile: {device_profile_data.get('name')}")

        try:
            response = self._make_request("POST", "/api/device-profiles", data)

            # Return the device profile ID
            result = {
                "id": response.get("id", ""),
                "name": data["deviceProfile"]["name"],
            }
            print(f"Created profile {result['name']} with ID: {result['id']}")
            return result
        except Exception as e:
            print(f"Error creating device profile: {str(e)}")
            raise

    def get_device_profile(self, device_profile_id: str) -> Dict[str, Any]:
        """Get a device profile from ChirpStack.

        Args:
            device_profile_id: Device profile ID

        Returns:
            Dict containing device profile information
        """
        response = self._make_request(
            "GET", f"/api/device-profiles/{device_profile_id}"
        )
        if "deviceProfile" in response:
            return response["deviceProfile"]
        return response

    def get_application_by_id(
        self, application_id: str, tenantId: str
    ) -> Dict[str, Any]:
        """Get an application by ID from ChirpStack.

        Args:
            application_id: Application ID

        Returns:
            Dict containing application information
        """
        return self.get_application(application_id, tenantId)

    def delete_device_profile(self, device_profile_id: str) -> bool:
        """Delete a device profile from ChirpStack.

        Args:
            device_profile_id: Device profile ID

        Returns:
            True if successful, raises exception otherwise
        """
        self._make_request("DELETE", f"/api/device-profiles/{device_profile_id}")
        return True
