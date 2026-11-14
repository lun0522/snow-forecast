"""US National Weather Service (api.weather.gov) gridpoints fetcher."""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Any

from app.geo import c_to_f, kph_to_mph, meters_to_feet, mm_to_inches
from app.http_client import get_json

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
    start_dt = datetime.fromisoformat(start_str.replace("Z", "+00:00")).astimezone(timezone.utc)
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
                "start": start_dt,
                "end": end_dt,
                "start_utc": start_dt.isoformat(),
                "end_utc": end_dt.isoformat(),
                "value": round(converter(float(val), uom), 3),
            }
        )
    return entries


def _sum_overlapping(entries: list[dict[str, Any]], win_start: datetime, win_end: datetime) -> float:
    """Proportionally sum interval-accumulated quantities overlapping [win_start, win_end)."""
    total = 0.0
    for entry in entries:
        e_start, e_end = entry["start"], entry["end"]
        duration_sec = (e_end - e_start).total_seconds()
        if duration_sec <= 0:
            continue
        overlap_start = max(e_start, win_start)
        overlap_end = min(e_end, win_end)
        if overlap_end > overlap_start:
            frac = (overlap_end - overlap_start).total_seconds() / duration_sec
            total += entry["value"] * frac
    return total


def _values_in_window(entries: list[dict[str, Any]], win_start: datetime, win_end: datetime) -> list[float]:
    return [
        e["value"]
        for e in entries
        if e["end"] > win_start and e["start"] < win_end
    ]


def _serialize_entries(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {"start_utc": e["start_utc"], "end_utc": e["end_utc"], "value": e["value"]}
        for e in entries
    ]


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


def parse_grid_forecast_response(
    payload: dict[str, Any],
    reference_time: datetime | None = None,
) -> dict[str, Any]:
    """Normalize NWS forecastGridData payload into metric/imperial series & window totals."""
    props = payload.get("properties") or {}
    update_time_raw = props.get("updateTime")
    ref = reference_time or datetime.now(timezone.utc)
    if reference_time is None and update_time_raw:
        ref = datetime.fromisoformat(update_time_raw.replace("Z", "+00:00")).astimezone(timezone.utc)

    qpf = _parse_layer(props, "quantitativePrecipitation", _to_mm)
    snow = _parse_layer(props, "snowfallAmount", _to_mm)
    snow_level = _parse_layer(props, "snowLevel", _to_meters)
    temp = _parse_layer(props, "temperature", _to_celsius)
    wind = _parse_layer(props, "windSpeed", _to_kph)
    gust = _parse_layer(props, "windGust", _to_kph)
    pop = _parse_layer(props, "probabilityOfPrecipitation", lambda v, _: v)

    elevation_info = props.get("elevation") or {}
    grid_elev_m = (
        _to_meters(float(elevation_info["value"]), elevation_info.get("unitCode"))
        if elevation_info.get("value") is not None
        else None
    )

    windows: dict[str, dict[str, Any]] = {}
    for hours in (24, 48, 72, 168):
        win_end = ref + timedelta(hours=hours)
        snow_mm = _sum_overlapping(snow, ref, win_end)
        qpf_mm = _sum_overlapping(qpf, ref, win_end)
        t_vals = _values_in_window(temp, ref, win_end)
        sl_vals = _values_in_window(snow_level, ref, win_end)
        w_vals = _values_in_window(wind, ref, win_end)
        g_vals = _values_in_window(gust, ref, win_end)

        windows[f"{hours}h"] = {
            "snowfall_in": round(mm_to_inches(snow_mm), 2),
            "snowfall_mm": round(snow_mm, 1),
            "precip_in": round(mm_to_inches(qpf_mm), 2),
            "precip_mm": round(qpf_mm, 1),
            "temp_min_f": round(c_to_f(min(t_vals)), 1) if t_vals else None,
            "temp_max_f": round(c_to_f(max(t_vals)), 1) if t_vals else None,
            "snow_level_min_ft": round(meters_to_feet(min(sl_vals))) if sl_vals else None,
            "snow_level_max_ft": round(meters_to_feet(max(sl_vals))) if sl_vals else None,
            "max_wind_mph": round(kph_to_mph(max(w_vals)), 1) if w_vals else None,
            "max_gust_mph": round(kph_to_mph(max(g_vals)), 1) if g_vals else None,
        }

    return {
        "source": "nws-gridpoints",
        "grid_id": props.get("gridId"),
        "update_time": update_time_raw,
        "grid_elevation_m": round(grid_elev_m, 1) if grid_elev_m is not None else None,
        "grid_elevation_ft": round(meters_to_feet(grid_elev_m)) if grid_elev_m is not None else None,
        "windows": windows,
        "layers": {
            "quantitative_precipitation_mm": _serialize_entries(qpf),
            "snowfall_amount_mm": _serialize_entries(snow),
            "snow_level_m": _serialize_entries(snow_level),
            "temperature_c": _serialize_entries(temp),
            "wind_speed_kph": _serialize_entries(wind),
            "wind_gust_kph": _serialize_entries(gust),
            "probability_of_precipitation_pct": _serialize_entries(pop),
        },
    }


def fetch_grid_forecast(forecast_grid_data_url: str) -> dict[str, Any]:
    """Fetch and parse NWS forecastGridData JSON from a discovered URL."""
    payload = get_json(forecast_grid_data_url)
    return parse_grid_forecast_response(payload)
