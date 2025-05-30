"""
CRUD operations for label history.
"""

from typing import List, Optional
from sqlalchemy.orm import Session

from app.models.label_history import LabelHistory


def get_label_history_by_id(db: Session, history_id: int) -> Optional[LabelHistory]:
    """
    Get a specific label history entry by ID.

    Args:
        db: Database session
        history_id: ID of the history entry to retrieve

    Returns:
        LabelHistory object or None if not found
    """
    return db.query(LabelHistory).filter(LabelHistory.id == history_id).first()


def get_label_history(
    db: Session,
    label_id: Optional[int] = None,
    label_ids: Optional[List[int]] = None,
    flow_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
) -> List[LabelHistory]:
    """
    Get label history entries with filtering options.

    Args:
        db: Database session
        label_id: Optional filter by specific label ID
        label_ids: Optional filter by list of label IDs
        flow_id: Optional filter by flow ID
        owner_id: Optional filter by owner ID
        skip: Number of records to skip (pagination)
        limit: Maximum number of records to return

    Returns:
        List of LabelHistory objects
    """
    query = db.query(LabelHistory)

    # Apply filters
    if label_id is not None:
        query = query.filter(LabelHistory.label_id == label_id)
    elif label_ids is not None and label_ids:
        query = query.filter(LabelHistory.label_id.in_(label_ids))

    if flow_id is not None:
        query = query.filter(LabelHistory.flow_id == flow_id)

    # Apply sorting and pagination
    return query.order_by(LabelHistory.timestamp.desc()).offset(skip).limit(limit).all()


def create_label_history(
    db: Session, label_id: int, flow_id: int, owner_id: int, action: str, data: dict
) -> LabelHistory:
    """
    Create a new label history entry.

    Args:
        db: Database session
        label_id: ID of the label
        flow_id: ID of the flow
        owner_id: ID of the owner
        action: Action performed on the label (e.g., "created", "updated", "deleted")
        data: Data associated with the history entry

    Returns:
        The created LabelHistory object
    """
    label_history = LabelHistory(
        label_id=label_id, flow_id=flow_id, owner_id=owner_id, action=action, data=data
    )
    db.add(label_history)
    db.commit()
    db.refresh(label_history)
    return label_history
