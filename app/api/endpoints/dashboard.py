from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, desc, or_
from sqlalchemy.orm import Session, aliased
from sqlalchemy.sql.expression import literal

from app import crud
from app.core.auth import jwt_auth
from app.db.database import get_db
from app.models.device import Device, DeviceStatus
from app.models.flow import Flow
from app.models.flow_history import FlowHistory
from app.models.function import Function
from app.models.function_history import FunctionHistory
from app.models.integration import Integration, IntegrationStatus
from app.models.user import User
from app.models.team import Team
from app.models.enums import OwnerType
from app.models.integration_history import IntegrationHistory

router = APIRouter()


@router.get("/stats", dependencies=[jwt_auth])
def get_dashboard_stats(
    *,
    db: Session = Depends(get_db),
    current_user: User = jwt_auth,
    team_id: Optional[int] = Query(None, description="Filter stats by specific team ID")
) -> Any:
    """
    Retrieve comprehensive dashboard statistics for devices, flows, functions, and integrations.

    This endpoint provides aggregated counts of resources and their statuses, serving
    as the primary data source for the dashboard visualization.

    Parameters:
    - **db**: Database session dependency
    - **current_user**: Authenticated user from JWT token
    - **team_id**: Optional filter to show only resources belonging to a specific team

    Returns:
    - Dictionary containing device, flow, function and integration statistics:
        - deviceStats: counts of total, online, offline, never seen and maintenance devices
        - flowStats: counts of total, successful, error, partial success, pending and inactive flows
        - functionStats: counts of total, active, error and inactive functions
        - integrationStats: counts of total, active, inactive and error integrations

    Access Control:
    - Users can only see statistics for their own resources or teams they belong to
    - Superusers can see statistics for all resources when not filtering by team
    """
    # Check team access if team_id is provided
    if team_id:
        # If team_id is provided, check if user belongs to this team
        team_exists = (
            db.query(Team)
            .filter(Team.id == team_id, Team.users.any(id=current_user.id))
            .first()
            is not None
        )

        if not current_user.is_superuser and not team_exists:
            # User is not a member of the requested team, return empty stats
            return {
                "deviceStats": {
                    "total": 0,
                    "online": 0,
                    "offline": 0,
                    "neverSeen": 0,
                    "maintenance": 0,
                },
                "flowStats": {
                    "total": 0,
                    "success": 0,
                    "error": 0,
                    "partialSuccess": 0,
                    "pending": 0,
                    "inactive": 0,
                },
                "functionStats": {"total": 0, "active": 0, "error": 0, "inactive": 0},
                "integrationStats": {
                    "total": 0,
                    "active": 0,
                    "inactive": 0,
                    "error": 0,
                },
            }

    # Build the ownership filters
    if current_user.is_superuser and not team_id:
        # Superusers can see everything when not filtering by team
        ownership_filter = True
        flow_ownership_filter = True
        function_ownership_filter = True
        integration_ownership_filter = True
    elif team_id:
        # If filtering by specific team, only show team resources
        ownership_filter = (Device.owner_id == team_id) & (
            Device.owner_type == OwnerType.TEAM
        )
        flow_ownership_filter = (Flow.owner_id == team_id) & (
            Flow.owner_type == OwnerType.TEAM
        )
        function_ownership_filter = (Function.owner_id == team_id) & (
            Function.owner_type == OwnerType.TEAM
        )
        integration_ownership_filter = (Integration.owner_id == team_id) & (
            Integration.owner_type == OwnerType.TEAM
        )
    else:
        # Only show user resources (default behavior)
        ownership_filter = (Device.owner_type == OwnerType.USER) & (
            Device.owner_id == current_user.id
        )
        flow_ownership_filter = (Flow.owner_type == OwnerType.USER) & (
            Flow.owner_id == current_user.id
        )
        function_ownership_filter = (Function.owner_type == OwnerType.USER) & (
            Function.owner_id == current_user.id
        )
        integration_ownership_filter = (Integration.owner_type == OwnerType.USER) & (
            Integration.owner_id == current_user.id
        )

    # Get device statistics - filter by ownership
    total_devices = (
        db.query(func.count(Device.id)).filter(ownership_filter).scalar() or 0
    )

    online_devices = (
        db.query(func.count(Device.id))
        .filter(ownership_filter, Device.status == DeviceStatus.ONLINE)
        .scalar()
        or 0
    )

    offline_devices = (
        db.query(func.count(Device.id))
        .filter(ownership_filter, Device.status == DeviceStatus.OFFLINE)
        .scalar()
        or 0
    )

    never_seen_devices = (
        db.query(func.count(Device.id))
        .filter(ownership_filter, Device.status == DeviceStatus.NEVER_SEEN)
        .scalar()
        or 0
    )

    maintenance_devices = (
        db.query(func.count(Device.id))
        .filter(
            ownership_filter,
            Device.status == DeviceStatus.MAINTENANCE,
        )
        .scalar()
        or 0
    )

    # Get flow statistics - filter by ownership
    total_flows = (
        db.query(func.count(Flow.id)).filter(flow_ownership_filter).scalar() or 0
    )

    # First, get the most recent history entry for each flow
    latest_flow_timestamps = (
        db.query(
            FlowHistory.flow_id,
            func.max(FlowHistory.timestamp).label("latest_timestamp"),
        )
        .join(Flow, FlowHistory.flow_id == Flow.id)
        .filter(flow_ownership_filter)  # Filter by ownership
        .group_by(FlowHistory.flow_id)
        .subquery()
    )

    # Now join back to get the status for each flow's latest history entry
    latest_flow_statuses = (
        db.query(FlowHistory.flow_id, FlowHistory.status)
        .join(
            latest_flow_timestamps,
            (FlowHistory.flow_id == latest_flow_timestamps.c.flow_id)
            & (FlowHistory.timestamp == latest_flow_timestamps.c.latest_timestamp),
        )
        .all()
    )

    # Count flows by their latest status
    flow_status_counts = {"success": 0, "error": 0, "partial_success": 0, "pending": 0}
    flow_ids_with_history = set()

    for flow_id, status in latest_flow_statuses:
        flow_ids_with_history.add(flow_id)
        if status == "success":
            flow_status_counts["success"] += 1
        elif status == "error":
            flow_status_counts["error"] += 1
        elif status == "partial_success":
            flow_status_counts["partial_success"] += 1
        elif status is None or status == "running":
            flow_status_counts["pending"] += 1

    # Inactive flows are those with no execution history
    inactive_flows = total_flows - len(flow_ids_with_history)

    # Get function statistics - filter by ownership
    total_functions = (
        db.query(func.count(Function.id)).filter(function_ownership_filter).scalar()
        or 0
    )

    # Get the most recent history entry for each function
    latest_function_timestamps = (
        db.query(
            FunctionHistory.function_id,
            func.max(FunctionHistory.timestamp).label("latest_timestamp"),
        )
        .join(Function, FunctionHistory.function_id == Function.id)
        .filter(function_ownership_filter)  # Filter by ownership
        .group_by(FunctionHistory.function_id)
        .subquery()
    )

    # Join back to get the status for each function's latest history entry
    latest_function_statuses = (
        db.query(FunctionHistory.function_id, FunctionHistory.status)
        .join(
            latest_function_timestamps,
            (FunctionHistory.function_id == latest_function_timestamps.c.function_id)
            & (
                FunctionHistory.timestamp
                == latest_function_timestamps.c.latest_timestamp
            ),
        )
        .all()
    )

    # Count functions by their latest status
    function_counts = {"active": 0, "error": 0}
    function_ids_with_history = set()

    for function_id, status in latest_function_statuses:
        function_ids_with_history.add(function_id)
        if status == "success":
            function_counts["active"] += 1
        elif status == "error":
            function_counts["error"] += 1

    # Inactive functions are those with no execution history
    inactive_functions = total_functions - len(function_ids_with_history)

    # Get integration statistics - filter by ownership
    total_integrations = (
        db.query(func.count(Integration.id))
        .filter(integration_ownership_filter)
        .scalar()
        or 0
    )

    # Get the most recent history entry for each integration
    latest_integration_timestamps = (
        db.query(
            IntegrationHistory.integration_id,
            func.max(IntegrationHistory.timestamp).label("latest_timestamp"),
        )
        .join(Integration, IntegrationHistory.integration_id == Integration.id)
        .filter(integration_ownership_filter)  # Filter by ownership
        .group_by(IntegrationHistory.integration_id)
        .subquery()
    )

    # Join back to get the status for each integration's latest history entry
    latest_integration_statuses = (
        db.query(IntegrationHistory.integration_id, IntegrationHistory.status)
        .join(
            latest_integration_timestamps,
            (
                IntegrationHistory.integration_id
                == latest_integration_timestamps.c.integration_id
            )
            & (
                IntegrationHistory.timestamp
                == latest_integration_timestamps.c.latest_timestamp
            ),
        )
        .all()
    )

    # Count integrations by their latest status
    integration_counts = {"active": 0, "error": 0}
    integration_ids_with_history = set()

    for integration_id, status in latest_integration_statuses:
        integration_ids_with_history.add(integration_id)
        if status == "success":
            integration_counts["active"] += 1
        elif status == "error":
            integration_counts["error"] += 1

    # Inactive integrations are those with no execution history
    inactive_integrations = total_integrations - len(integration_ids_with_history)

    # Compile all statistics
    return {
        "deviceStats": {
            "total": total_devices,
            "online": online_devices,
            "offline": offline_devices,
            "neverSeen": never_seen_devices,
            "maintenance": maintenance_devices,
        },
        "flowStats": {
            "total": total_flows,
            "success": flow_status_counts["success"],
            "error": flow_status_counts["error"],
            "partialSuccess": flow_status_counts["partial_success"],
            "pending": flow_status_counts["pending"],
            "inactive": inactive_flows,
        },
        "functionStats": {
            "total": total_functions,
            "active": function_counts["active"],
            "error": function_counts["error"],
            "inactive": inactive_functions,
        },
        "integrationStats": {
            "total": total_integrations,
            "active": integration_counts["active"],
            "inactive": inactive_integrations,
            "error": integration_counts["error"],
        },
    }
