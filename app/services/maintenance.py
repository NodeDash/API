from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from typing import Dict, Any

from app.models.device_history import DeviceHistory
from app.models.flow_history import FlowHistory
from app.models.function_history import FunctionHistory
from app.models.integration_history import IntegrationHistory
from app.models.label_history import LabelHistory


def cleanup_history_data(db: Session, retention_days: int = 1) -> Dict[str, int]:
    """
    Clean up history tables by removing data older than the specified retention period.

    Args:
        db: Database session
        retention_days: Number of days to retain data (default: 1)

    Returns:
        dict: Count of deleted records for each table
    """
    cutoff_date = datetime.utcnow() - timedelta(days=retention_days)

    # Delete old records from each history table
    device_deleted = (
        db.query(DeviceHistory)
        .filter(DeviceHistory.timestamp < cutoff_date)
        .delete(synchronize_session=False)
    )

    flow_deleted = (
        db.query(FlowHistory)
        .filter(FlowHistory.timestamp < cutoff_date)
        .delete(synchronize_session=False)
    )

    function_deleted = (
        db.query(FunctionHistory)
        .filter(FunctionHistory.timestamp < cutoff_date)
        .delete(synchronize_session=False)
    )

    integration_deleted = (
        db.query(IntegrationHistory)
        .filter(IntegrationHistory.timestamp < cutoff_date)
        .delete(synchronize_session=False)
    )

    label_deleted = (
        db.query(LabelHistory)
        .filter(LabelHistory.timestamp < cutoff_date)
        .delete(synchronize_session=False)
    )

    # Commit the changes
    db.commit()

    return {
        "device_history": device_deleted,
        "flow_history": flow_deleted,
        "function_history": function_deleted,
        "integration_history": integration_deleted,
        "label_history": label_deleted,
    }
