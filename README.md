# Device Manager API

A comprehensive API for managing IoT devices, integrations, and data flows. Built with FastAPI and PostgreSQL.

## Overview

The Device Manager API provides a complete backend solution for IoT device management with support for:

- Device registration and monitoring
- Device grouping through labels
- Integration with external systems via HTTP and MQTT
- Custom JavaScript functions for data transformation
- Flow-based automation for routing and processing device data
- Comprehensive execution history and logging

## System Architecture

```
┌───────────────┐     ┌───────────────┐     ┌───────────────┐     ┌───────────────┐
│   IoT Device  │────▶│     Helium    │────▶│  ChirpStack   │────▶│   Ingest API  │
└───────────────┘     └───────────────┘     └───────────────┘     └───────┬───────┘
                                                                          │
                                                                          │
                                                                          ▼
                                                                  ┌───────────────┐
                                                                  │ Flow Engine   │
                                                                  └───────┬───────┘
                                                                          │
                                                                          │
                                                                          ▼
┌───────────────┐     ┌───────────────┐                          ┌───────────────┐
│  HTTP Service │◀────┤ Integrations  │◀─────────────────────────┤   Functions   │
└───────────────┘     └───────┬───────┘                          └───────────────┘
                              │
                              │
                              ▼
                      ┌───────────────┐
                      │  MQTT Broker  │
                      └───────────────┘
```

## Project Structure

The project follows a modular architecture for better maintainability and separation of concerns:

```
device-manager-api/
├── alembic.ini                 # Alembic configuration for migrations
├── migrations/                 # Database migrations
├── requirements.txt            # Python dependencies
├── app/                        # Main application package
│   ├── main.py                 # Application entry point
│   ├── api/                    # API layer
│   │   ├── api.py              # API router configuration
│   │   └── endpoints/          # API endpoints by resource
│   │       ├── devices.py      # Device endpoints
│   │       ├── flows.py        # Flow endpoints
│   │       ├── functions.py    # Function endpoints
│   │       ├── ingest.py       # Data ingestion endpoints
│   │       ├── integrations.py # Integration endpoints
│   │       ├── labels.py       # Label endpoints
│   │       └── storage.py     # Storage endpoints
│   ├── core/                   # Core application components
│   │   └── config.py           # Application configuration
│   ├── crud/                   # Database operations
│   │   ├── device.py           # Device CRUD operations
│   │   ├── flow.py             # Flow CRUD operations
│   │   ├── function.py         # Function CRUD operations
│   │   ├── integration.py      # Integration CRUD operations
│   │   ├── label.py            # Label CRUD operations
│   │   └── storage.py          # Storage CRUD operations
│   ├── db/                     # Database setup
│   │   └── database.py         # Database connection and session
│   ├── models/                 # SQLAlchemy models
│   │   ├── device.py           # Device model
│   │   ├── device_history.py   # Device history model
│   │   ├── flow.py             # Flow model
│   │   ├── flow_history.py     # Flow execution history model
│   │   ├── function.py         # Function model
│   │   ├── function_history.py # Function execution history model
│   │   ├── integration.py      # Integration model
│   │   ├── integration_history.py # Integration execution history model
│   │   ├── label.py            # Label model
│   │   └── storage.py          # Storage model
│   ├── schemas/                # Pydantic schemas for validation
│   │   ├── chirpstack.py       # ChirpStack data schemas
│   │   ├── device.py           # Device schemas
│   │   ├── device_history.py   # Device history schemas
│   │   ├── flow.py             # Flow schemas
│   │   ├── function.py         # Function schemas
│   │   ├── integration.py      # Integration schemas
│   │   ├── label.py            # Label schemas
│   │   └── storage.py          # Storage schemas
│   └── services/               # Business logic services
│       ├── flow_processor.py   # Flow execution engine
│       └── integrations/       # Integration clients
│           ├── __init__.py     # Package exports
│           ├── http_client.py  # HTTP integration client
│           └── mqtt_client.py  # MQTT integration client
```

## Installation

### Prerequisites

- Python 3.8+
- PostgreSQL 12+
- Git

### Setup

1. Clone the repository:

   ```bash
   git clone <repository-url>
   cd device-manager-api
   ```

2. Create a virtual environment:

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. Set up environment variables (create a `.env` file):

   ```
   DATABASE_URL=postgresql://user:password@localhost/device_manager
   API_HOST=0.0.0.0
   API_PORT=8000
   DEBUG=True
   SECRET_KEY=your_secure_secret_key
   LOG_LEVEL=INFO
   ```

5. Set up the database:

   ```bash
   # Create the database
   createdb device_manager

   # Generate and apply migrations
   alembic revision --autogenerate -m "Initial migration"
   alembic upgrade head
   ```

6. Start the API server:
   ```bash
   uvicorn app.main:app --reload
   ```

## Authentication

The API uses JWT (JSON Web Token) authentication. To authenticate with the API:

1. **Register a user** (if you don't have an account yet):

   ```
   POST /api/v1/auth/register
   ```

   with JSON body:

   ```json
   {
     "email": "user@example.com",
     "username": "johndoe",
     "password": "securepassword"
   }
   ```

2. **Login to obtain a token**:

   ```
   POST /api/v1/auth/login
   ```

   with form data:

   ```
   username=user@example.com&password=securepassword
   ```

3. **Use the token in subsequent requests** by adding it to the Authorization header:
   ```
   Authorization: Bearer <your_token>
   ```

### Create an Admin User

You can create an initial admin user using the provided script:

```bash
python create_admin_user.py <email> <username> <password>
```

Example:

```bash
python create_admin_user.py admin@example.com admin securepassword
```

## API Endpoints

### Device Management

- `GET /api/v1/devices` - List all devices
- `POST /api/v1/devices` - Create a new device
- `GET /api/v1/devices/{device_id}` - Get device details
- `PUT /api/v1/devices/{device_id}` - Update a device
- `DELETE /api/v1/devices/{device_id}` - Delete a device
- `GET /api/v1/devices/history` - Get history for all devices
- `GET /api/v1/devices/{device_id}/history` - Get history for a specific device
- `GET /api/v1/devices/{device_id}/labels` - Get all labels assigned to a device
- `PUT /api/v1/devices/{device_id}/labels` - Update the labels assigned to a device

### Label Management

- `GET /api/v1/labels` - List all labels
- `POST /api/v1/labels` - Create a new label
- `GET /api/v1/labels/{label_id}` - Get label details
- `PUT /api/v1/labels/{label_id}` - Update a label
- `DELETE /api/v1/labels/{label_id}` - Delete a label
- `POST /api/v1/labels/{label_id}/devices/{device_id}` - Add device to a label
- `DELETE /api/v1/labels/{label_id}/devices/{device_id}` - Remove device from a label

### Function Management

- `GET /api/v1/functions` - List all functions
- `POST /api/v1/functions` - Create a new function
- `GET /api/v1/functions/{function_id}` - Get function details
- `PUT /api/v1/functions/{function_id}` - Update a function
- `DELETE /api/v1/functions/{function_id}` - Delete a function
- `GET /api/v1/functions/history` - Get history for all functions
- `GET /api/v1/functions/{function_id}/history` - Get function execution history

### Integration Management

- `GET /api/v1/integrations` - List all integrations
- `POST /api/v1/integrations` - Create a new integration
- `GET /api/v1/integrations/{integration_id}` - Get integration details
- `PUT /api/v1/integrations/{integration_id}` - Update an integration
- `DELETE /api/v1/integrations/{integration_id}` - Delete an integration
- `GET /api/v1/integrations/history` - Get history for all integrations
- `GET /api/v1/integrations/{integration_id}/history` - Get integration execution history
- `GET /api/v1/integrations/{integration_id}/history/{history_id}` - Get detailed integration history record

### Flow Management

- `GET /api/v1/flows` - List all flows
- `POST /api/v1/flows` - Create a new flow
- `GET /api/v1/flows/{flow_id}` - Get flow details
- `PUT /api/v1/flows/{flow_id}` - Update a flow
- `DELETE /api/v1/flows/{flow_id}` - Delete a flow
- `GET /api/v1/flows/history` - Get history for all flows
- `GET /api/v1/flows/{flow_id}/history` - Get flow execution history
- `GET /api/v1/flows/{flow_id}/history/{history_id}` - Get detailed flow history record

### Storage Management

- `GET /api/v1/storages` - List all storage configurations
- `POST /api/v1/storages` - Create a new storage configuration
- `GET /api/v1/storages/{storage_id}` - Get storage details
- `PUT /api/v1/storages/{storage_id}` - Update a storage configuration
- `DELETE /api/v1/storages/{storage_id}` - Delete a storage configuration

### Search

- `GET /api/v1/search?query=searchterm` - Search across devices, functions, flows, and integrations

### Data Ingestion

- `POST /api/v1/ingest/chirpstack` - Ingest device uplink data from ChirpStack

## Core Components

### 1. Models Layer

The models represent database tables and relationships:

- **Device**: Represents IoT devices with their metadata
- **Label**: Allows grouping and categorizing devices
- **Function**: Stores JavaScript functions for data transformation
- **Integration**: Defines external system connections (HTTP/MQTT)
- **Flow**: Contains node and edge definitions for data flow
- **History models**: Track execution details and status

### 2. CRUD Layer

Provides database operations for each model:

- Create new records
- Read existing records
- Update record data
- Delete records
- Query with filtering and pagination

### 3. Services Layer

Contains business logic separated from API endpoints:

- **Flow processor**: Executes flows, processes nodes, and records history
- **Integration clients**: Communicate with external systems via HTTP and MQTT

### 4. API Layer

Exposes HTTP endpoints for client applications:

- RESTful endpoints for all resources
- Request validation
- Response formatting
- Error handling

## Core Concepts

### Devices

Devices are the core entities in the system, representing physical IoT devices. Each device has:

- A unique identifier (DEV EUI)
- Name and description
- Status (online/offline)
- Metadata and configuration options

### Labels

Labels allow grouping devices for easier management and targeting in flows. A device can have multiple labels.

### Functions

Functions contain JavaScript code that can transform data. They are used in flows to process device data before sending it to integrations. For example:

```javascript
function processTemperature(data) {
  // Convert Celsius to Fahrenheit
  if (data.data.temperature) {
    data.data.temperatureF = (data.data.temperature * 9) / 5 + 32;
  }
  return data;
}
```

### Integrations

Integrations define connections to external systems. Two types are supported:

1. **HTTP Integration**: Send data to a web endpoint

   - URL, method, headers
   - SSL/TLS support

2. **MQTT Integration**: Publish data to an MQTT broker
   - Host, port, topic, credentials
   - Optional SSL/TLS support

### Flows

Flows connect devices, functions, and integrations to create automated data processing pipelines. A flow consists of:

- Nodes (devices, labels, functions, integrations)
- Edges connecting these nodes
- Configuration for each node

When a device sends an uplink, matching flows are triggered, executing functions and sending data to integrations according to the defined path.

### Execution Logging

The system keeps detailed logs of:

- Device uplinks
- Function executions (input, output, errors)
- Integration calls (request, response, errors)
- Flow executions (path, status, timing)

## Flow Processing

When a device sends an uplink, the following happens:

1. The uplink is received via the `/api/v1/ingest/chirpstack` endpoint
2. The system identifies the device by its DEV EUI
3. The uplink is stored in device history
4. All labels associated with the device are identified
5. Flows that reference this device or its labels are found
6. For each matching flow:
   - The system follows the flow's edges from the trigger node
   - Functions are executed to transform the data
   - Data is sent to integrations
   - All execution details are logged

The flow processor handles the execution of functions and integrations, recording detailed execution history:

- **Success**: When all nodes execute successfully
- **Partial success**: When some nodes succeed and others fail
- **Error**: When all paths in the flow fail

## Example Scenarios

### Temperature Monitoring

1. Create a temperature sensor device
2. Create an "alert" function that checks if temperature exceeds a threshold
3. Create an HTTP integration to send alerts
4. Create a flow connecting the device → alert function → HTTP integration
5. When the device reports a high temperature, an alert is automatically sent

### Asset Tracking

1. Register asset tracking devices with a "trackers" label
2. Create a "location-processor" function to format coordinates
3. Create an MQTT integration to publish location updates
4. Create a flow: trackers label → location-processor → MQTT integration
5. All tracker devices now automatically publish formatted location updates

## Development and Extension

### Adding New Endpoints

1. Create a new file in `app/api/endpoints/`
2. Define your router and endpoints
3. Add the router to `app/api/api.py`

### Adding New Models

1. Create a new model file in `app/models/`
2. Define SQLAlchemy model classes
3. Create corresponding schema in `app/schemas/`
4. Add CRUD operations in `app/crud/`

### Adding New Services

1. Create a new service module in `app/services/`
2. Implement business logic functions
3. Keep services stateless and focused on specific tasks
4. Use dependency injection for database sessions

### Database Migrations

When changing models:

```bash
# Generate migration
alembic revision --autogenerate -m "Description of changes"

# Apply migration
alembic upgrade head
```

## Monitoring and Debugging

### Logging

The system uses Python's logging module to record events at different levels:

- **INFO**: Normal operations (successful requests, flow executions)
- **WARNING**: Issues that don't prevent operation (partial successes)
- **ERROR**: Problems that need attention (failed executions, connection errors)
- **DEBUG**: Detailed information for troubleshooting

Logs include:

- Execution times for functions, integrations, and flows
- Success/failure status for each component
- Input/output data for debugging

### Performance Considerations

- Database queries are optimized to minimize load
- Asynchronous HTTP calls prevent blocking
- Processing is modular to allow scaling individual components

## API Security

- HTTPS for all communications
- API key authentication
- Role-based access control
- Input validation for all endpoints

## Troubleshooting

### Common Issues

- **Database connection error**: Check your DATABASE_URL in the .env file
- **MQTT connection failures**: Verify broker settings and credentials
- **Function execution errors**: Check function logs for JavaScript errors
- **Flow processing issues**: Examine the flow history records for specific failure points

### Debugging Tips

1. Enable DEBUG level logging to see more details
2. Check function history records to inspect input/output data
3. Look at integration history to verify request/response details
4. Use the GET history endpoints to investigate execution paths
