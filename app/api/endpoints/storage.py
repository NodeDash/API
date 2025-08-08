from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.core.auth import get_current_active_user, check_resource_permissions
from app.models.provider import Provider
from app.models.enums import ProviderType
from app.schemas.storage import (
    WritePoint,
    WritePointsBody,
    QueryParams,
    UpsertBody,
    DeleteBody,
)
from app.crud import provider as provider_crud
from app.services.storage.influxdb_client import InfluxDBStorageClient

router = APIRouter()


def _get_influx_client_from_provider(provider: Provider) -> InfluxDBStorageClient:
    if provider.provider_type != ProviderType.influxdb:
        raise HTTPException(
            status_code=400, detail="Provider is not an InfluxDB provider"
        )
    cfg = provider.config or {}
    url = cfg.get("url")
    org = cfg.get("org")
    bucket = cfg.get("bucket")
    token = cfg.get("token")
    verify_ssl = cfg.get("verify_ssl", True)
    precision = cfg.get("precision", "ns")
    if not (url and org and bucket and token):
        raise HTTPException(
            status_code=400,
            detail="Provider config missing required InfluxDB fields (url, org, bucket, token)",
        )
    return InfluxDBStorageClient(
        url=url,
        org=org,
        bucket=bucket,
        token=token,
        verify_ssl=verify_ssl,
        precision=precision,
    )


@router.post("/{provider_id}/write", response_model=bool)
def write_points(
    provider_id: int,
    body: WritePointsBody,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    provider = provider_crud.get_provider(db, provider_id)
    check_resource_permissions(db, current_user, provider, "write")

    client = _get_influx_client_from_provider(provider)
    try:
        client.write_points([p.model_dump() for p in body.points], bucket=body.bucket)
        return True
    finally:
        client.close()


@router.post("/{provider_id}/upsert", response_model=bool)
def upsert_point(
    provider_id: int,
    body: UpsertBody,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    provider = provider_crud.get_provider(db, provider_id)
    check_resource_permissions(db, current_user, provider, "write")

    client = _get_influx_client_from_provider(provider)
    try:
        client.upsert_point(body.model_dump())
        return True
    finally:
        client.close()


@router.post("/{provider_id}/query", response_model=List[Dict[str, Any]])
def query_points(
    provider_id: int,
    params: QueryParams,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    provider = provider_crud.get_provider(db, provider_id)
    check_resource_permissions(db, current_user, provider, "read")

    client = _get_influx_client_from_provider(provider)
    try:
        res = client.query_range(
            start=params.start,
            end=params.end,
            measurement=params.measurement,
            tags=params.tags,
            fields=params.fields,
            agg=params.agg,
            window=params.window,
            limit=params.limit,
            offset=params.offset,
            order=params.order or "desc",
            bucket=params.bucket,
        )
        return res
    finally:
        client.close()


@router.post("/{provider_id}/delete", response_model=bool)
def delete_points(
    provider_id: int,
    body: DeleteBody,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    provider = provider_crud.get_provider(db, provider_id)
    check_resource_permissions(db, current_user, provider, "delete")

    client = _get_influx_client_from_provider(provider)
    try:
        client.delete_range(
            start=body.start,
            end=body.end,
            measurement=body.measurement,
            predicate=body.predicate,
            tags=body.tags,
            bucket=body.bucket,
        )
        return True
    finally:
        client.close()
