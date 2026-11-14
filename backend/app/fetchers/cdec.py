"""California Data Exchange Center (CDEC) snow sensor fetcher."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

from app.http_client import HttpFetchError, get_json

CDEC_JSON_URL = "https://cdec.water.ca.gov/dynamicapp/req/JSONDataServlet"

# CDEC standard snow sensors:
# 3 = Snow Water Content (inches), 18 = Snow Depth (inches), 4 = Air Temperature (F)
DEFAULT_CDEC_SENSORS: dict[int, str] = {
    3: "swe_in",
    18: "snow_depth_in",
    4: "temp_f",
}

_INVALID_VALUES = {None, "", "---", "ART", "BRT", -9999, -9999.0, -999, "-9999"}


def _clean_numeric(raw: Any) -> float | None:
    if raw in _INVALID_VALUES:
        return None
    try:
        val = float(raw)
    except (TypeError, ValueError):
        return None
    if val <= -999.0:
        return None
    return val


def _normalize_cdec_timestamp(raw_ts: str) -> str:
    """Zero-pad unpadded CDEC dates (e.g. '2026-11-9 00:00' -> '2026-11-09 00:00')."""
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(raw_ts.strip(), fmt)
            return dt.strftime("%Y-%m-%d %H:%M") if " " in raw_ts else dt.strftime("%Y-%m-%d")
        except ValueError:
            continue
    return raw_ts


def parse_cdec_sensor_rows(
    rows: list[dict[str, Any]],
    metric_name: str | None = None,
) -> list[dict[str, Any]]:
    """Filter sentinel values and normalize CDEC JSONDataServlet rows."""
    cleaned: list[dict[str, Any]] = []
    for row in rows:
        raw_ts = row.get("date") or row.get("obsDate")
        val = _clean_numeric(row.get("value"))
        if not raw_ts or val is None:
            continue
        ts = _normalize_cdec_timestamp(str(raw_ts))

        sensor_num = row.get("SENSOR_NUM") or row.get("sensorNum")
        resolved_metric = metric_name or (
            DEFAULT_CDEC_SENSORS.get(int(sensor_num)) if sensor_num is not None else None
        )
        if not resolved_metric:
            continue

        if resolved_metric in ("swe_in", "snow_depth_in") and val < 0.0:
            val = 0.0

        cleaned.append(
            {
                "timestamp": ts,
                "metric": resolved_metric,
                "value": round(val, 2),
                "units": row.get("units"),
            }
        )
    return cleaned


def fetch_cdec_station_data(
    station_id: str,
    days_back: int = 7,
    duration: str = "D",
    end_day: date | None = None,
) -> dict[str, Any]:
    """Fetch SWE, Snow Depth, and Temp from CDEC JSONDataServlet for a California snow station."""
    anchor = end_day or date.today()
    start = anchor - timedelta(days=days_back)
    end = anchor + timedelta(days=1)

    by_ts: dict[str, dict[str, Any]] = {}
    sensor_list = ",".join(str(s) for s in DEFAULT_CDEC_SENSORS.keys())
    try:
        payload = get_json(
            CDEC_JSON_URL,
            params={
                "Stations": station_id.upper(),
                "SensorNums": sensor_list,
                "dur_code": duration,
                "start_date": start.isoformat(),
                "end_date": end.isoformat(),
            },
        )
    except HttpFetchError:
        payload = []

    if isinstance(payload, list):
        for entry in parse_cdec_sensor_rows(payload):
            row = by_ts.setdefault(entry["timestamp"], {"timestamp": entry["timestamp"]})
            row[entry["metric"]] = entry["value"]

    series = [by_ts[k] for k in sorted(by_ts.keys())]
    latest = series[-1] if series else {}
    return {
        "station_id": station_id.upper(),
        "source": "cdec",
        "duration": duration,
        "latest": latest,
        "observations": series,
    }
