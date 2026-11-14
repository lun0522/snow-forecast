"""Open-Meteo multi-model mountain weather and DEM elevation fetcher."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from app.geo import c_to_f, cm_to_inches, kph_to_mph, meters_to_feet, mm_to_inches
from app.http_client import get_json

OPEN_METEO_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
OPEN_METEO_ELEVATION_URL = "https://api.open-meteo.com/v1/elevation"

DEFAULT_MODELS: tuple[str, ...] = (
    "ecmwf_ifs025",
    "gfs_global",
    "gfs_hrrr",
    "ncep_nbm_conus",
    "gem_global",
    "icon_global",
)

HOURLY_VARIABLES: tuple[str, ...] = (
    "temperature_2m",
    "relative_humidity_2m",
    "precipitation",
    "rain",
    "snowfall",
    "snow_depth",
    "freezing_level_height",
    "wind_speed_10m",
    "wind_gusts_10m",
    "wind_direction_10m",
    "weather_code",
)

SUMMARY_WINDOWS_HOURS: tuple[int, ...] = (24, 48, 72, 168, 240)


def fetch_dem_elevations(
    coords: list[tuple[float, float]],
    timeout: float = 8.0,
    retries: int = 1,
) -> list[float | None]:
    """Fetch Copernicus 90m DEM elevations (meters) from Open-Meteo."""
    if not coords:
        return []
    lats = ",".join(f"{lat:.5f}" for lat, _ in coords)
    lons = ",".join(f"{lon:.5f}" for _, lon in coords)
    payload = get_json(
        OPEN_METEO_ELEVATION_URL,
        params={"latitude": lats, "longitude": lons},
        timeout=timeout,
        retries=retries,
    )
    elevations = payload.get("elevation") or []
    return [float(e) if e is not None else None for e in elevations]


def _extract_series(hourly: dict[str, Any], var: str, model: str, total_len: int) -> list[Any]:
    """Read variable values for a model, supporting both multi-model suffixes and single-model keys."""
    suffixed = f"{var}_{model}"
    if suffixed in hourly:
        return hourly[suffixed]
    if var in hourly:
        return hourly[var]
    return [None] * total_len


def _parse_utc_hour(ts: str) -> datetime:
    """Parse Open-Meteo ISO timestamp (UTC) into an aware datetime."""
    if ts.endswith("Z"):
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    dt = datetime.fromisoformat(ts)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _summarize_model_hours(rows: list[dict[str, Any]], reference_time: datetime) -> dict[str, Any]:
    """Compute horizon coverage and snowfall/precip/temp/wind summaries for standard windows."""
    valid_rows = [
        r
        for r in rows
        if r["snowfall_cm"] is not None or r["precip_mm"] is not None or r["temp_c"] is not None
    ]
    if not valid_rows:
        return {"max_horizon_hours": 0, "windows": {}}

    last_dt = max(_parse_utc_hour(r["time_utc"]) for r in valid_rows)
    max_horizon_hours = max(0, int(round((last_dt - reference_time).total_seconds() / 3600.0)) + 1)

    windows: dict[str, dict[str, Any]] = {}
    for hours in SUMMARY_WINDOWS_HOURS:
        cutoff = reference_time + timedelta(hours=hours)
        slice_rows = [
            r
            for r in valid_rows
            if reference_time <= _parse_utc_hour(r["time_utc"]) < cutoff
        ]
        snow_vals = [r["snowfall_cm"] for r in slice_rows if r["snowfall_cm"] is not None]
        precip_vals = [r["precip_mm"] for r in slice_rows if r["precip_mm"] is not None]
        temp_vals = [r["temp_c"] for r in slice_rows if r["temp_c"] is not None]
        wind_vals = [r["wind_kph"] for r in slice_rows if r["wind_kph"] is not None]
        gust_vals = [r["wind_gust_kph"] for r in slice_rows if r["wind_gust_kph"] is not None]
        fl_vals = [r["freezing_level_m"] for r in slice_rows if r["freezing_level_m"] is not None]

        # Only populate a window if the model covers at least 75% of it (avoid misleading 48h HRRR 7d totals).
        if len(slice_rows) < int(hours * 0.75):
            continue

        snow_cm = sum(snow_vals) if snow_vals else 0.0
        precip_mm = sum(precip_vals) if precip_vals else 0.0
        windows[f"{hours}h"] = {
            "hours_covered": len(slice_rows),
            "snowfall_cm": round(snow_cm, 2),
            "snowfall_in": round(cm_to_inches(snow_cm), 2),
            "precip_mm": round(precip_mm, 2),
            "precip_in": round(mm_to_inches(precip_mm), 2),
            "temp_min_f": round(c_to_f(min(temp_vals)), 1) if temp_vals else None,
            "temp_max_f": round(c_to_f(max(temp_vals)), 1) if temp_vals else None,
            "max_wind_mph": round(kph_to_mph(max(wind_vals)), 1) if wind_vals else None,
            "max_gust_mph": round(kph_to_mph(max(gust_vals)), 1) if gust_vals else None,
            "freezing_level_min_ft": round(meters_to_feet(min(fl_vals))) if fl_vals else None,
            "freezing_level_max_ft": round(meters_to_feet(max(fl_vals))) if fl_vals else None,
        }

    return {"max_horizon_hours": max_horizon_hours, "windows": windows}


def parse_multi_model_response(
    payload: dict[str, Any],
    models: tuple[str, ...] | list[str],
    reference_time: datetime | None = None,
) -> dict[str, Any]:
    """Normalize an Open-Meteo multi-model forecast response into per-model series & summaries."""
    hourly = payload.get("hourly") or {}
    times: list[str] = hourly.get("time") or []
    if reference_time is not None:
        ref = reference_time
    elif times:
        now_hour = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
        first_dt = _parse_utc_hour(times[0])
        last_dt = _parse_utc_hour(times[-1])
        ref = now_hour if first_dt <= now_hour <= last_dt else first_dt
    else:
        ref = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)

    model_results: dict[str, Any] = {}
    for model in models:
        temp_s = _extract_series(hourly, "temperature_2m", model, len(times))
        rh_s = _extract_series(hourly, "relative_humidity_2m", model, len(times))
        precip_s = _extract_series(hourly, "precipitation", model, len(times))
        rain_s = _extract_series(hourly, "rain", model, len(times))
        snow_s = _extract_series(hourly, "snowfall", model, len(times))
        depth_s = _extract_series(hourly, "snow_depth", model, len(times))
        fl_s = _extract_series(hourly, "freezing_level_height", model, len(times))
        wind_s = _extract_series(hourly, "wind_speed_10m", model, len(times))
        gust_s = _extract_series(hourly, "wind_gusts_10m", model, len(times))
        dir_s = _extract_series(hourly, "wind_direction_10m", model, len(times))
        code_s = _extract_series(hourly, "weather_code", model, len(times))

        rows: list[dict[str, Any]] = []
        for idx, ts in enumerate(times):
            rows.append(
                {
                    "time_utc": ts if ts.endswith("Z") else f"{ts}Z",
                    "temp_c": temp_s[idx],
                    "temp_f": round(c_to_f(temp_s[idx]), 1) if temp_s[idx] is not None else None,
                    "rh_pct": rh_s[idx],
                    "precip_mm": precip_s[idx],
                    "precip_in": round(mm_to_inches(precip_s[idx]), 3) if precip_s[idx] is not None else None,
                    "rain_mm": rain_s[idx],
                    "snowfall_cm": snow_s[idx],
                    "snowfall_in": round(cm_to_inches(snow_s[idx]), 2) if snow_s[idx] is not None else None,
                    "snow_depth_m": depth_s[idx],
                    "freezing_level_m": fl_s[idx],
                    "freezing_level_ft": round(meters_to_feet(fl_s[idx])) if fl_s[idx] is not None else None,
                    "wind_kph": wind_s[idx],
                    "wind_mph": round(kph_to_mph(wind_s[idx]), 1) if wind_s[idx] is not None else None,
                    "wind_gust_kph": gust_s[idx],
                    "wind_gust_mph": round(kph_to_mph(gust_s[idx]), 1) if gust_s[idx] is not None else None,
                    "wind_dir_deg": dir_s[idx],
                    "weather_code": code_s[idx],
                }
            )

        summary = _summarize_model_hours(rows, ref)
        model_results[model] = {
            "summary": summary,
            "hourly": rows,
        }

    return {
        "source": "open-meteo",
        "grid_latitude": payload.get("latitude"),
        "grid_longitude": payload.get("longitude"),
        "downscaled_elevation_m": payload.get("elevation"),
        "models": model_results,
    }


def fetch_multi_model_forecast(
    lat: float,
    lon: float,
    elevation_m: float | None = None,
    models: tuple[str, ...] | list[str] = DEFAULT_MODELS,
    forecast_days: int = 10,
    timeout: float = 10.0,
    retries: int = 1,
) -> dict[str, Any]:
    """Fetch and parse hourly multi-model forecast from Open-Meteo for a point & elevation."""
    params: dict[str, Any] = {
        "latitude": f"{lat:.5f}",
        "longitude": f"{lon:.5f}",
        "hourly": ",".join(HOURLY_VARIABLES),
        "models": ",".join(models),
        "forecast_days": forecast_days,
        "timezone": "UTC",
    }
    if elevation_m is not None:
        params["elevation"] = round(elevation_m, 1)

    payload = get_json(OPEN_METEO_FORECAST_URL, params=params, timeout=timeout, retries=retries)
    return parse_multi_model_response(payload, models=models)
