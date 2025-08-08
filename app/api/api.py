from fastapi import APIRouter

from app.api.endpoints import (
    devices,
    labels,
    integrations,
    functions,
    flows,
    search,
    auth,
    dashboard,
    teams,
    providers,
    maintenance,
    storage,
)

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])
api_router.include_router(devices.router, prefix="/devices", tags=["Devices"])
api_router.include_router(labels.router, prefix="/labels", tags=["Labels"])
api_router.include_router(
    integrations.router, prefix="/integrations", tags=["Integrations"]
)
api_router.include_router(functions.router, prefix="/functions", tags=["Functions"])
api_router.include_router(flows.router, prefix="/flows", tags=["Flows"])
api_router.include_router(providers.router, prefix="/providers", tags=["Providers"])
api_router.include_router(
    maintenance.router, prefix="/maintenance", tags=["Maintenance"]
)
api_router.include_router(storage.router, prefix="/storage", tags=["Storage"])

api_router.include_router(search.router, prefix="/search", tags=["Search"])
api_router.include_router(teams.router, prefix="/teams", tags=["Teams"])
