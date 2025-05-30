"""
CRUD operations for function history.
"""

import json
from typing import List, Optional
from sqlalchemy.orm import Session

from app.models.function_history import FunctionHistory


def safe_serialize_json(data):
    """
    Safely serialize data to JSON, handling problematic values like NaN.

    Args:
        data: The data to serialize

    Returns:
        JSON serialized string that's safe for database storage
    """
    if data is None:
        return None

    # Handle special case of already being a string
    if isinstance(data, str):
        try:
            # Test if already valid JSON
            json.loads(data)
            return data
        except (ValueError, TypeError):
            # Not valid JSON, wrap in a dict
            return json.dumps({"data": data})

    # Replace NaN values with None
    if isinstance(data, dict):
        sanitized = {}
        for key, value in data.items():
            if isinstance(value, float) and value != value:  # NaN check
                sanitized[key] = None
            elif isinstance(value, dict):
                sanitized[key] = safe_serialize_json(value)
            elif isinstance(value, list):
                sanitized[key] = [
                    None if (isinstance(v, float) and v != v) else v for v in value
                ]
            else:
                sanitized[key] = value
        data = sanitized

    try:
        return json.dumps(data, default=lambda o: str(o))
    except (TypeError, ValueError, OverflowError) as e:
        print(f"Error serializing function history data: {e}")
        return json.dumps({"error": "Failed to serialize data", "message": str(e)})


def get_function_history_by_id(
    db: Session, history_id: int
) -> Optional[FunctionHistory]:
    """
    Get a specific function history entry by ID.

    Args:
        db: Database session
        history_id: ID of the history entry to retrieve

    Returns:
        FunctionHistory object or None if not found
    """
    return db.query(FunctionHistory).filter(FunctionHistory.id == history_id).first()


def get_function_history(
    db: Session,
    function_id: Optional[int] = None,
    function_ids: Optional[List[int]] = None,
    flowId: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
) -> List[FunctionHistory]:
    """
    Get function history entries with filtering options.

    Args:
        db: Database session
        function_id: Optional filter by specific function ID
        function_ids: Optional filter by list of function IDs
        skip: Number of records to skip (pagination)
        limit: Maximum number of records to return

    Returns:
        List of FunctionHistory objects
    """
    query = db.query(FunctionHistory)

    # Apply filters
    if function_id is not None:
        query = query.filter(FunctionHistory.function_id == function_id)
    elif function_ids is not None and function_ids:
        query = query.filter(FunctionHistory.function_id.in_(function_ids))

    if flowId is not None:
        query = query.filter(FunctionHistory.flow_id == flowId)

    # Apply sorting and pagination
    return (
        query.order_by(FunctionHistory.timestamp.desc()).offset(skip).limit(limit).all()
    )


def create_function_history(
    db: Session,
    function_id: int,
    status: str,
    input_data: dict,
    output_data: dict,
    error: Optional[str] = None,
) -> FunctionHistory:
    """
    Create a new function history entry.

    Args:
        db: Database session
        function_id: ID of the function
        status: Status of the function execution (success, error)
        input_data: Input data for the function execution
        output_data: Output data from the function execution
        error: Optional error message if the function execution failed

    Returns:
        The created FunctionHistory object
    """
    function_history = FunctionHistory(
        function_id=function_id,
        status=status,
        input_data=safe_serialize_json(input_data),
        output_data=safe_serialize_json(output_data),
        error=error,
    )
    db.add(function_history)
    db.commit()
    db.refresh(function_history)
    return function_history


def update_function_history(
    db: Session,
    function_history_id: int,
    status: str,
    output_data: dict = None,
    execution_time: int = None,
) -> bool:
    """
    Update a function history record with execution results.

    Args:
        db: Database session
        function_history_id: ID of the function history record to update
        status: New status value ('success', 'error', etc.)
        output_data: Output data from function execution
        execution_time: Execution time in milliseconds

    Returns:
        Boolean indicating success of the update
    """
    try:
        history = (
            db.query(FunctionHistory)
            .filter(FunctionHistory.id == function_history_id)
            .first()
        )

        if not history:
            print(f"Function history record not found: {function_history_id}")
            return False

        # Update fields
        history.status = status

        # Handle output data safely
        if output_data is not None:
            # Sanitize and serialize the output data
            history.output_data = safe_serialize_json(output_data)

        if execution_time is not None:
            history.execution_time = execution_time

        db.add(history)
        db.commit()
        return True

    except Exception as e:
        print(f"Error updating function history: {str(e).split('[SQL:')[0]}")
        db.rollback()

        # Try once more with simplified data
        try:
            history = (
                db.query(FunctionHistory)
                .filter(FunctionHistory.id == function_history_id)
                .first()
            )

            if history:
                history.status = status
                history.output_data = json.dumps(
                    {"error": "Data contained non-serializable values"}
                )

                if execution_time is not None:
                    history.execution_time = execution_time

                db.add(history)
                db.commit()
                return True
        except Exception as e2:
            print(
                f"Second attempt to update function history failed: {str(e2).split('[SQL:')[0]}"
            )
            db.rollback()

        return False
