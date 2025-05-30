from typing import Any, Dict
from fastapi import APIRouter, Depends, Query, Security
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.services.maintenance import cleanup_history_data
from app.core.auth import api_key_header
from app.core.config import settings

router = APIRouter()


@router.post("/cleanup-history")
def run_history_cleanup(
    *,
    db: Session = Depends(get_db),
    retention_days: int = Query(1, description="Number of days to retain data"),
    api_key: str = Security(api_key_header),
) -> Dict[str, Any]:
    """
    Run cleanup of history tables to retain only data within the specified retention period.

    This endpoint triggers the removal of historical data older than the specified
    retention period from all history tables (device, flow, function, integration, label).
    It helps maintain database performance and manage storage requirements.

    Parameters:
    - **db**: Database session dependency
    - **retention_days**: Number of days of history to keep (default: 1)
    - **api_key**: API key for authentication

    Returns:
    - Object with success status, deleted counts per history table, and a message

    Security:
    - Requires a valid API key matching the system's SECRET_KEY
    - Typically invoked by automated maintenance processes rather than users

    Notes:
    - This is a potentially resource-intensive operation on large databases
    - Consider running during low-usage periods
    - Deleted data cannot be recovered
    """

    if api_key != settings.SECRET_KEY:
        return {
            "success": False,
            "error": "Invalid API key",
        }

    result = cleanup_history_data(db, retention_days)
    return {
        "success": True,
        "deleted_counts": result,
        "message": "History cleanup completed successfully",
    }
