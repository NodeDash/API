"""
CRUD operations for flow history.
"""

import json
from typing import List, Optional
from sqlalchemy.orm import Session

from app.models.flow_history import FlowHistory


def get_flow_history_by_id(db: Session, history_id: int) -> Optional[FlowHistory]:
    """
    Get a specific flow history entry by ID.

    Args:
        db: Database session
        history_id: ID of the history entry to retrieve

    Returns:
        FlowHistory object or None if not found
    """
    history = db.query(FlowHistory).filter(FlowHistory.id == history_id).first()
    if history:
        _deserialize_json_fields(history)
    return history


def get_flow_history(
    db: Session,
    flow_id: Optional[int] = None,
    flow_ids: Optional[List[int]] = None,
    skip: int = 0,
    limit: int = 100,
) -> List[FlowHistory]:
    """
    Get flow history entries with filtering options.

    Args:
        db: Database session
        flow_id: Optional filter by specific flow ID
        flow_ids: Optional filter by list of flow IDs
        skip: Number of records to skip (pagination)
        limit: Maximum number of records to return

    Returns:
        List of FlowHistory objects
    """
    query = db.query(FlowHistory)

    # Apply filters
    if flow_id is not None:
        query = query.filter(FlowHistory.flow_id == flow_id)
    elif flow_ids is not None and flow_ids:
        query = query.filter(FlowHistory.flow_id.in_(flow_ids))

    # Apply sorting and pagination
    history_entries = (
        query.order_by(FlowHistory.timestamp.desc()).offset(skip).limit(limit).all()
    )

    # Process JSON fields for all entries
    for history in history_entries:
        _deserialize_json_fields(history)

    return history_entries


def create_flow_history(
    db: Session,
    flow_id: int,
    status: str,
    input_data: dict,
    output_data: dict,
    error: Optional[str] = None,
) -> FlowHistory:
    """
    Create a new flow history entry.

    Args:
        db: Database session
        flow_id: ID of the flow
        status: Status of the flow execution (success, error, partial)
        input_data: Input data for the flow execution
        output_data: Output data from the flow execution
        error: Optional error message if the flow execution failed

    Returns:
        The created FlowHistory object
    """

    # Handle JSON serialization for input_data
    serialized_input_data = _safe_serialize_json(input_data)

    # Handle JSON serialization for output_data
    serialized_output_data = _safe_serialize_json(output_data)

    # Create the flow history record
    flow_history = FlowHistory(
        flow_id=flow_id,
        status=status,
        input_data=serialized_input_data,
        output_data=serialized_output_data,
        error_details=error,  # Assuming this is the correct field name based on models
    )
    db.add(flow_history)
    db.commit()
    db.refresh(flow_history)

    # Convert the JSON back to objects for return
    _deserialize_json_fields(flow_history)

    return flow_history


def _safe_serialize_json(data):
    """
    Safely serialize data to JSON, handling special values like NaN.

    Args:
        data: The data to serialize to JSON

    Returns:
        Serialized JSON data that's safe for PostgreSQL
    """
    if data is None:
        return None

    if not isinstance(data, dict) and not isinstance(data, list):
        try:
            # Try to parse it if it's already a string
            data = json.loads(data) if isinstance(data, str) else {"data": str(data)}
        except (ValueError, TypeError):
            data = {"data": str(data)}

    try:
        # Use a custom handler for non-serializable values
        return json.dumps(data, default=lambda o: str(o))
    except (TypeError, ValueError, OverflowError) as e:
        print(f"Error serializing JSON data: {str(e)}")
        return json.dumps({"error": f"Failed to serialize data: {str(e)}"})


def _deserialize_json_fields(history):
    """
    Deserialize JSON fields in a FlowHistory object.

    Args:
        history: The FlowHistory object to process
    """
    # Handle execution_path field
    if history.execution_path:
        if isinstance(history.execution_path, str):
            try:
                history.execution_path = json.loads(history.execution_path)
            except (ValueError, TypeError) as e:
                print(f"Error deserializing execution_path: {str(e)}")
                history.execution_path = []

    # Handle error_details field - convert from string to list if needed
    if history.error_details:
        if isinstance(history.error_details, str):
            try:
                if history.error_details.startswith(
                    "["
                ) and history.error_details.endswith("]"):
                    history.error_details = json.loads(history.error_details)
            except (ValueError, TypeError) as e:
                # Keep as string if it's not valid JSON
                pass

    # Handle input_data field
    if history.input_data:
        if isinstance(history.input_data, str):
            try:
                history.input_data = json.loads(history.input_data)
            except (ValueError, TypeError) as e:
                print(f"Error deserializing input_data: {str(e)}")
                history.input_data = {"error": "Failed to deserialize input data"}

    # Handle output_data field
    if history.output_data:
        if isinstance(history.output_data, str):
            try:
                history.output_data = json.loads(history.output_data)
            except (ValueError, TypeError) as e:
                print(f"Error deserializing output_data: {str(e)}")
                history.output_data = {"error": "Failed to deserialize output data"}
