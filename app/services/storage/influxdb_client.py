from __future__ import annotations

from typing import Any, Dict, List, Optional
from datetime import datetime

from influxdb_client import InfluxDBClient, Point, WritePrecision


class InfluxDBStorageClient:
    """
    Thin wrapper around influxdb-client for write/query/delete operations.
    Expects provider.config to contain:
      {
        "url": "https://us-east-1-1.aws.cloud2.influxdata.com",
        "org": "my-org",
        "bucket": "my-bucket",
        "token": "...",
        "verify_ssl": true,
        "precision": "ns"|"us"|"ms"|"s"
      }
    """

    def __init__(
        self,
        url: str,
        org: str,
        bucket: str,
        token: str,
        verify_ssl: bool = True,
        precision: str = "ns",
    ):
        self.url = url
        self.org = org
        self.bucket = bucket
        self.token = token
        self.verify_ssl = verify_ssl
        self.precision = precision

        self._client = InfluxDBClient(
            url=self.url, token=self.token, org=self.org, verify_ssl=self.verify_ssl
        )
        self._write_api = self._client.write_api()
        self._query_api = self._client.query_api()
        self._delete_api = self._client.delete_api()

    def _precision_to_write_precision(self, precision: Optional[str]) -> WritePrecision:
        p = (precision or self.precision or "ns").lower()
        if p == "ns":
            return WritePrecision.NS
        if p == "us":
            return WritePrecision.US
        if p == "ms":
            return WritePrecision.MS
        if p == "s":
            return WritePrecision.S
        return WritePrecision.NS

    def write_points(
        self, points: List[Dict[str, Any]], bucket: Optional[str] = None
    ) -> None:
        """
        points: [{ measurement, tags: {}, fields: {}, timestamp?: str|datetime, precision?: str }]
        """
        influx_points: List[Any] = []
        for p in points:
            measurement = p.get("measurement")
            if not measurement:
                raise ValueError("measurement is required for each point")
            tags = p.get("tags") or {}
            fields = p.get("fields") or {}
            timestamp = p.get("timestamp")
            precision = p.get("precision")

            pt = Point(measurement)
            for k, v in tags.items():
                if v is not None:
                    pt = pt.tag(str(k), str(v))
            for k, v in fields.items():
                # influxdb-client will infer types; ensure not None
                if v is not None:
                    pt = pt.field(str(k), v)

            if timestamp is not None:
                if isinstance(timestamp, datetime):
                    pt = pt.time(
                        timestamp,
                        write_precision=self._precision_to_write_precision(precision),
                    )
                else:
                    # Expect ISO8601 string
                    dt = datetime.fromisoformat(str(timestamp).replace("Z", "+00:00"))
                    pt = pt.time(
                        dt,
                        write_precision=self._precision_to_write_precision(precision),
                    )

            influx_points.append(pt)

        if influx_points:
            self._write_api.write(
                bucket=bucket or self.bucket, org=self.org, record=influx_points
            )

    def upsert_point(self, point: Dict[str, Any], bucket: Optional[str] = None) -> None:
        """
        Writes a single point with exact series (measurement+tags) and timestamp to overwrite fields.
        """
        self.write_points([point], bucket=bucket)

    def _build_filters(
        self,
        measurement: Optional[str],
        tags: Optional[Dict[str, str]],
        fields: Optional[List[str]],
    ) -> str:
        filters: List[str] = []
        if measurement:
            filters.append(f'r["_measurement"] == "{measurement}"')
        if tags:
            for k, v in tags.items():
                filters.append(f'r["{k}"] == "{v}"')
        if fields:
            # filter for specific field names
            field_pred = " or ".join([f'r["_field"] == "{f}"' for f in fields])
            filters.append(f"({field_pred})")
        if not filters:
            return "true"
        return " and ".join(filters)

    def query_range(
        self,
        start: str,
        end: Optional[str] = None,
        measurement: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None,
        fields: Optional[List[str]] = None,
        agg: Optional[str] = None,
        window: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        order: str = "desc",
        bucket: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        start/end can be RFC3339 timestamps (e.g., 2025-08-08T00:00:00Z) or relative (e.g., -7d). If end is None, uses now().
        """
        # Build Flux query
        bkt = bucket or self.bucket
        rng = f"|> range(start: {start}, stop: {end or 'now()'})"
        flt = self._build_filters(measurement, tags, fields)
        query = f'from(bucket: "{bkt}") {rng} |> filter(fn: (r) => {flt})'

        if agg and window:
            query += (
                f" |> aggregateWindow(every: {window}, fn: {agg}, createEmpty: false)"
            )
        elif agg:
            # If agg provided without window, use groupThen agg (not typical). Skipping.
            pass

        if order == "asc":
            query += ' |> sort(columns: ["_time"], desc: false)'
        else:
            query += ' |> sort(columns: ["_time"], desc: true)'

        if offset:
            query += f" |> offset(n: {int(offset)})"
        if limit:
            query += f" |> limit(n: {int(limit)})"

        tables = self._query_api.query(query, org=self.org)
        results: List[Dict[str, Any]] = []
        for table in tables:
            for record in table.records:
                item = {
                    "time": record.get_time().isoformat(),
                    "measurement": record.get_measurement(),
                    "field": record.get_field(),
                    "value": record.get_value(),
                    "tags": {},
                }
                # include tag columns
                for k, v in record.values.items():
                    if k.startswith("_"):
                        continue
                    if k in ("result", "table"):  # internal
                        continue
                    # For standard tags, record has columns beyond _time/_value/_field/_measurement
                    if k not in ("_time", "_value", "_field", "_measurement"):
                        item["tags"][k] = v
                results.append(item)
        return results

    def delete_range(
        self,
        start: str,
        end: str,
        measurement: Optional[str] = None,
        predicate: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None,
        bucket: Optional[str] = None,
    ) -> None:
        """
        Delete points for a range with optional predicate; if predicate not supplied, build from measurement/tags.
        start/end must be RFC3339 strings (e.g., 2025-08-08T00:00:00Z).
        """
        pred = predicate
        if pred is None:
            clauses: List[str] = []
            if measurement:
                clauses.append(f'_measurement="{measurement}"')
            if tags:
                for k, v in tags.items():
                    clauses.append(f'{k}="{v}"')
            pred = " and ".join(clauses) if clauses else ""

        self._delete_api.delete(
            start, end, pred, bucket=bucket or self.bucket, org=self.org
        )

    def close(self):
        try:
            self._client.close()
        except Exception:
            pass
