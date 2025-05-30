"""
CRUD operations for integration history.
"""

from typing import List, Optional
from sqlalchemy.orm import Session

from app.models.integration_history import IntegrationHistory


def get_integration_history_by_id(
    db: Session, history_id: int
) -> Optional[IntegrationHistory]:
    """
    Get a specific integration history entry by ID.

    Args:
        db: Database session
        history_id: ID of the history entry to retrieve

    Returns:
        IntegrationHistory object or None if not found
    """
    return (
        db.query(IntegrationHistory).filter(IntegrationHistory.id == history_id).first()
    )


def get_integration_history(
    db: Session,
    integration_id: Optional[int] = None,
    integration_ids: Optional[List[int]] = None,
    flowId: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
) -> List[IntegrationHistory]:
    """
    Get integration history entries with filtering options.

    Args:
        db: Database session
        integration_id: Optional filter by specific integration ID
        integration_ids: Optional filter by list of integration IDs
        skip: Number of records to skip (pagination)
        limit: Maximum number of records to return

    Returns:
        List of IntegrationHistory objects
    """
    query = db.query(IntegrationHistory)

    # Apply filters
    if integration_id is not None:
        query = query.filter(IntegrationHistory.integration_id == integration_id)
    elif integration_ids is not None and integration_ids:
        query = query.filter(IntegrationHistory.integration_id.in_(integration_ids))

    if flowId is not None:
        query = query.filter(IntegrationHistory.flow_id == flowId)

    # Apply sorting and pagination
    return (
        query.order_by(IntegrationHistory.timestamp.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def create_integration_history(
    db: Session,
    integration_id: int,
    status: str,
    request_data: dict,
    response_data: dict,
    error: Optional[str] = None,
) -> IntegrationHistory:
    """
    Create a new integration history entry.

    Args:
        db: Database session
        integration_id: ID of the integration
        status: Status of the integration execution (success, error)
        request_data: Request data sent to the integration
        response_data: Response data received from the integration
        error: Optional error message if the integration execution failed

    Returns:
        The created IntegrationHistory object
    """
    integration_history = IntegrationHistory(
        integration_id=integration_id,
        status=status,
        request_data=request_data,
        response_data=response_data,
        error=error,
    )
    db.add(integration_history)
    db.commit()
    db.refresh(integration_history)
    return integration_history
