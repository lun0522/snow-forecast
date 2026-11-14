"""US National Weather Service (api.weather.gov) gridpoints fetcher."""

from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import Any

from app.http_client import get_json
from app.time_utils import parse_utc

NWS_POINTS_URL = "https://api.weather.gov/points"
_ISO_DURATION_RE = re.compile(
    r"^P(?:(?P<days>\d+)D)?(?:T(?:(?P<hours>\d+)H)?(?:(?P<minutes>\d+)M)?(?:(?P<seconds>\d+)S)?)?$"
)


def parse_iso_duration(duration_str: str) -> timedelta:
    """Parse ISO8601 duration strings such as PT1H, PT6H, P1DT12H."""
    match = _ISO_DURATION_RE.match(duration_str)
    if not match:
        raise ValueError(f"Unsupported ISO8601 duration: {duration_str}")
    return timedelta(
        days=int(match.group("days") or 0),
        hours=int(match.group("hours") or 0),
        minutes=int(match.group("minutes") or 0),
        seconds=int(match.group("seconds") or 0),
    )


def parse_valid_time(valid_time: str) -> tuple[datetime, datetime]:
    """Split NWS 'start/duration' validTime into aware UTC (start, end) datetimes."""
    start_str, dur_str = valid_time.split("/", 1)
    start_dt = parse_utc(start_str)
    duration = parse_iso_duration(dur_str)
    return start_dt, start_dt + duration


def _to_mm(value: float, uom: str | None) -> float:
    if uom in (None, "wmoUnit:mm", "unit:mm"):
        return value
    if uom in ("wmoUnit:cm", "unit:cm"):
        return value * 10.0
    if uom in ("wmoUnit:m", "unit:m"):
        return value * 1000.0
    if uom in ("wmoUnit:in", "unit:in"):
        return value * 25.4
    return value


def _to_meters(value: float, uom: str | None) -> float:
    if uom in (None, "wmoUnit:m", "unit:m"):
        return value
    if uom in ("wmoUnit:km", "unit:km"):
        return value * 1000.0
    if uom in ("wmoUnit:ft", "unit:ft", "wmoUnit:ft_i"):
        return value * 0.3048
    return value


def _to_celsius(value: float, uom: str | None) -> float:
    if uom in (None, "wmoUnit:degC", "unit:degC"):
        return value
    if uom in ("wmoUnit:degF", "unit:degF"):
        return (value - 32.0) * 5.0 / 9.0
    if uom in ("wmoUnit:K", "unit:K"):
        return value - 273.15
    return value


def _to_kph(value: float, uom: str | None) -> float:
    if uom in (None, "wmoUnit:km_h-1", "unit:km_h-1"):
        return value
    if uom in ("wmoUnit:m_s-1", "unit:m_s-1"):
        return value * 3.6
    if uom in ("wmoUnit:kt", "unit:kt"):
        return value * 1.852
    return value


def _parse_layer(props: dict[str, Any], key: str, converter) -> list[dict[str, Any]]:
    layer = props.get(key) or {}
    uom = layer.get("uom")
    entries: list[dict[str, Any]] = []
    for item in layer.get("values") or []:
        val = item.get("value")
        vt = item.get("validTime")
        if val is None or not vt:
            continue
        start_dt, end_dt = parse_valid_time(vt)
        entries.append(
            {
                "start_utc": start_dt.isoformat(),
                "end_utc": end_dt.isoformat(),
                "value": round(converter(float(val), uom), 3),
            }
        )
    return entries


def discover_gridpoint(lat: float, lon: float) -> dict[str, Any]:
    """Query /points/{lat},{lon} to discover NWS WFO grid coordinates and endpoints."""
    payload = get_json(f"{NWS_POINTS_URL}/{lat:.4f},{lon:.4f}")
    props = payload.get("properties") or {}
    rel = (props.get("relativeLocation") or {}).get("properties") or {}
    return {
        "grid_id": props.get("gridId"),
        "grid_x": props.get("gridX"),
        "grid_y": props.get("gridY"),
        "forecast_grid_data_url": props.get("forecastGridData"),
        "forecast_hourly_url": props.get("forecastHourly"),
        "observation_stations_url": props.get("observationStations"),
        "relative_city": rel.get("city"),
        "relative_state": rel.get("state"),
    }


def parse_grid_forecast_response(payload: dict[str, Any]) -> dict[str, Any]:
    """Normalize NWS forecastGridData payload into metric interval layers."""
    props = payload.get("properties") or {}
    return {
        "source": "nws-gridpoints",
        "grid_id": props.get("gridId"),
        "update_time": props.get("updateTime"),
        "layers": {
            "quantitative_precipitation_mm": _parse_layer(props, "quantitativePrecipitation", _to_mm),
            "snowfall_amount_mm": _parse_layer(props, "snowfallAmount", _to_mm),
            "snow_level_m": _parse_layer(props, "snowLevel", _to_meters),
            "temperature_c": _parse_layer(props, "temperature", _to_celsius),
            "wind_speed_kph": _parse_layer(props, "windSpeed", _to_kph),
            "wind_gust_kph": _parse_layer(props, "windGust", _to_kph),
        },
    }


def fetch_grid_forecast(forecast_grid_data_url: str) -> dict[str, Any]:
    """Fetch and parse NWS forecastGridData JSON from a discovered URL."""
    payload = get_json(forecast_grid_data_url)
    return parse_grid_forecast_response(payload)
