from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_, func

from app.core.auth import jwt_auth  # Changed from api_key_auth to jwt_auth
from app.db.database import get_db
from app.models.device import Device
from app.models.function import Function
from app.models.integration import Integration
from app.models.flow import Flow
from app.models.team import Team
from app.models.user import User
from app.models.enums import OwnerType
from app.crud import team as crud_team

router = APIRouter()


@router.get(
    "/",
    response_model=Dict[str, List[Dict[str, Any]]],
    dependencies=[jwt_auth],  # Changed to JWT auth
)
def search_resources(
    query: str = Query(..., description="Search term"),
    resource_types: Optional[str] = Query(
        None,
        description="Comma-separated list of resource types to search (devices, functions, flows, integrations). If not provided, searches all types.",
    ),
    limit: int = Query(10, description="Maximum number of results per resource type"),
    team_id: Optional[int] = Query(
        None, description="Filter results by specific team ID"
    ),
    db: Session = Depends(get_db),
    current_user: User = jwt_auth,
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Search across different resources (devices, functions, flows, integrations).

    You can optionally limit the search to specific resource types.

    By default, only shows resources owned by the current user.
    If team_id is provided, shows resources owned by that specific team.

    Authentication:
        Requires a valid JWT token
    """
    results = {}
    resource_list = (
        resource_types.split(",")
        if resource_types
        else ["devices", "functions", "flows", "integrations"]
    )

    # Convert query to lowercase for case-insensitive search
    search_term = f"%{query.lower()}%"

    # Determine team access
    if team_id:
        # If team_id is provided, check if user belongs to this team
        team_exists = (
            db.query(Team)
            .filter(Team.id == team_id, Team.users.any(id=current_user.id))
            .first()
            is not None
        )

        if not current_user.is_superuser and not team_exists:
            # User is not a member of the requested team, show no results
            return {"devices": [], "functions": [], "flows": [], "integrations": []}

    # Build the ownership filters for each resource type
    if current_user.is_superuser and not team_id:
        # Superusers can see everything when not filtering by team
        device_ownership_filter = True
        function_ownership_filter = True
        flow_ownership_filter = True
        integration_ownership_filter = True
    elif team_id:
        # If filtering by specific team, only show team resources
        device_ownership_filter = (Device.owner_id == team_id) & (
            Device.owner_type == OwnerType.TEAM
        )
        function_ownership_filter = (Function.owner_id == team_id) & (
            Function.owner_type == OwnerType.TEAM
        )
        flow_ownership_filter = (Flow.owner_id == team_id) & (
            Flow.owner_type == OwnerType.TEAM
        )
        integration_ownership_filter = (Integration.owner_id == team_id) & (
            Integration.owner_type == OwnerType.TEAM
        )
    else:
        # Only show user resources (default behavior)
        device_ownership_filter = (Device.owner_type == OwnerType.USER) & (
            Device.owner_id == current_user.id
        )
        function_ownership_filter = (Function.owner_type == OwnerType.USER) & (
            Function.owner_id == current_user.id
        )
        flow_ownership_filter = (Flow.owner_type == OwnerType.USER) & (
            Flow.owner_id == current_user.id
        )
        integration_ownership_filter = (Integration.owner_type == OwnerType.USER) & (
            Integration.owner_id == current_user.id
        )

    # Search devices
    if "devices" in resource_list:
        devices = (
            db.query(Device)
            .filter(
                device_ownership_filter,
                or_(
                    func.lower(Device.name).like(search_term),
                    func.lower(Device.dev_eui).like(search_term),
                    func.lower(Device.app_eui).like(search_term),
                ),
            )
            .limit(limit)
            .all()
        )

        results["devices"] = [
            {
                "id": device.id,
                "name": device.name,
                "type": "device",
                "dev_eui": device.dev_eui,
                "status": device.status,
                "owner_type": device.owner_type,
                "owner_id": device.owner_id,
            }
            for device in devices
        ]

    # Search functions
    if "functions" in resource_list:
        functions = (
            db.query(Function)
            .filter(
                function_ownership_filter,
                or_(
                    func.lower(Function.name).like(search_term),
                    (
                        func.lower(Function.description).like(search_term)
                        if Function.description
                        else False
                    ),
                ),
            )
            .limit(limit)
            .all()
        )

        results["functions"] = [
            {
                "id": function.id,
                "name": function.name,
                "type": "function",
                "description": function.description,
                "owner_type": function.owner_type,
                "owner_id": function.owner_id,
            }
            for function in functions
        ]

    # Search flows
    if "flows" in resource_list:
        flows = (
            db.query(Flow)
            .filter(
                flow_ownership_filter,
                or_(
                    func.lower(Flow.name).like(search_term),
                    (
                        func.lower(Flow.description).like(search_term)
                        if Flow.description
                        else False
                    ),
                ),
            )
            .limit(limit)
            .all()
        )

        results["flows"] = [
            {
                "id": flow.id,
                "name": flow.name,
                "type": "flow",
                "description": flow.description,
                "owner_type": flow.owner_type,
                "owner_id": flow.owner_id,
            }
            for flow in flows
        ]

    # Search integrations
    if "integrations" in resource_list:
        integrations = (
            db.query(Integration)
            .filter(
                integration_ownership_filter,
                or_(
                    func.lower(Integration.name).like(search_term),
                    (
                        func.lower(Integration.description).like(search_term)
                        if Integration.description
                        else False
                    ),
                ),
            )
            .limit(limit)
            .all()
        )

        results["integrations"] = [
            {
                "id": integration.id,
                "name": integration.name,
                "type": "integration",
                "description": integration.description,
                "owner_type": integration.owner_type,
                "owner_id": integration.owner_id,
            }
            for integration in integrations
        ]

    return results
