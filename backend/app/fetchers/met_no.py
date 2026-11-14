"""MET Norway Locationforecast 2.0 fetcher (ECMWF-backed, altitude-adjusted)."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from app.geo import cm_to_inches
from app.http_client import get_json
from app.time_utils import parse_utc

MET_NO_COMPLETE_URL = "https://api.met.no/weatherapi/locationforecast/2.0/complete"


def _mps_to_mph(mps: float) -> float:
    return mps * 2.23693629


def _estimate_snow_fraction(symbol_code: str | None, temp_c: float | None) -> float:
    """Estimate fraction of precipitation falling as snow from MET symbol_code & temp."""
    code = (symbol_code or "").lower()
    if "snow" in code:
        return 1.0
    if "sleet" in code:
        return 0.5
    if "rain" in code:
        return 0.0
    if temp_c is not None:
        if temp_c <= 0.0:
            return 1.0
        if temp_c <= 1.5:
            return 0.5
    return 0.0


def _preliminary_slr(temp_c: float | None) -> float:
    """Simple temperature-based SLR estimate before Step 3 physics engine."""
    if temp_c is None:
        return 10.0
    if temp_c <= -10.0:
        return 15.0
    if temp_c <= -5.0:
        return 13.0
    if temp_c <= -2.0:
        return 11.0
    if temp_c <= 0.5:
        return 8.5
    return 6.0


def parse_met_no_response(payload: dict[str, Any]) -> dict[str, Any]:
    """Normalize MET Norway Locationforecast 2.0 JSON into non-overlapping intervals."""
    props = payload.get("properties") or {}
    meta = props.get("meta") or {}
    timeseries = props.get("timeseries") or []
    coords = (payload.get("geometry") or {}).get("coordinates") or []
    altitude_m = float(coords[2]) if len(coords) >= 3 else None

    if not timeseries:
        return {
            "source": "met-no",
            "updated_at": meta.get("updated_at"),
            "altitude_m": altitude_m,
            "intervals": [],
        }

    times = [parse_utc(item["time"]) for item in timeseries]
    intervals: list[dict[str, Any]] = []
    for idx, item in enumerate(timeseries):
        t_start = times[idx]
        data = item.get("data") or {}
        instant = (data.get("instant") or {}).get("details") or {}

        # Choose interval block matching step width to avoid double-counting 1h and 6h summaries.
        next_step_hours = (
            (times[idx + 1] - t_start).total_seconds() / 3600.0
            if idx + 1 < len(times)
            else 6.0
        )

        block_name: str | None = None
        block_hours = 0.0
        if next_step_hours <= 1.5 and "next_1_hours" in data:
            block_name = "next_1_hours"
            block_hours = 1.0
        elif next_step_hours <= 6.5 and "next_6_hours" in data:
            block_name = "next_6_hours"
            block_hours = 6.0
        elif "next_1_hours" in data:
            block_name = "next_1_hours"
            block_hours = 1.0
        elif "next_6_hours" in data:
            block_name = "next_6_hours"
            block_hours = 6.0
        elif "next_12_hours" in data:
            block_name = "next_12_hours"
            block_hours = 12.0

        block = data.get(block_name) or {} if block_name else {}
        summary = block.get("summary") or {}
        details = block.get("details") or {}

        temp_c = instant.get("air_temperature")
        wind_mps = instant.get("wind_speed")
        gust_mps = instant.get("wind_speed_of_gust")
        precip_mm = details.get("precipitation_amount")
        symbol_code = summary.get("symbol_code")

        snow_frac = _estimate_snow_fraction(symbol_code, temp_c)
        snow_qpf_mm = float(precip_mm) * snow_frac if precip_mm is not None else 0.0
        # 1 mm liquid * (SLR/10) cm = snow_cm (since 1 mm water at 10:1 -> 1 cm snow)
        est_snow_cm = snow_qpf_mm * (_preliminary_slr(temp_c) / 10.0)

        t_end = t_start + timedelta(hours=block_hours) if block_hours > 0 else t_start
        intervals.append(
            {
                "start_utc": t_start.isoformat(),
                "end_utc": t_end.isoformat(),
                "temp_c": temp_c,
                "rh_pct": instant.get("relative_humidity"),
                "wind_mph": round(_mps_to_mph(float(wind_mps)), 1) if wind_mps is not None else None,
                "wind_gust_mph": round(_mps_to_mph(float(gust_mps)), 1) if gust_mps is not None else None,
                "precip_mm": round(float(precip_mm), 2) if precip_mm is not None else None,
                "est_snow_in": round(cm_to_inches(est_snow_cm), 2) if precip_mm is not None else None,
            }
        )

    return {
        "source": "met-no",
        "updated_at": meta.get("updated_at"),
        "altitude_m": altitude_m,
        "intervals": intervals,
    }


def fetch_met_no_forecast(
    lat: float,
    lon: float,
    elevation_m: float | None = None,
) -> dict[str, Any]:
    """Fetch MET Norway Locationforecast 2.0 complete JSON for a coordinate and altitude."""
    params: dict[str, Any] = {
        "lat": f"{lat:.4f}",
        "lon": f"{lon:.4f}",
    }
    if elevation_m is not None:
        params["altitude"] = int(round(elevation_m))
    payload = get_json(MET_NO_COMPLETE_URL, params=params)
    return parse_met_no_response(payload)
