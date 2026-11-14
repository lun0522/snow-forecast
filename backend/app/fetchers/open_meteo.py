"""Open-Meteo multi-model mountain weather and DEM elevation fetcher."""

from __future__ import annotations

from typing import Any

from app.geo import cm_to_inches, kph_to_mph
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
    "snowfall",
    "freezing_level_height",
    "wind_speed_10m",
    "wind_gusts_10m",
)


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


def parse_multi_model_response(
    payload: dict[str, Any],
    models: tuple[str, ...] | list[str],
) -> dict[str, Any]:
    """Normalize an Open-Meteo multi-model forecast response into per-model hourly series."""
    hourly = payload.get("hourly") or {}
    times: list[str] = hourly.get("time") or []

    model_results: dict[str, Any] = {}
    for model in models:
        temp_s = _extract_series(hourly, "temperature_2m", model, len(times))
        rh_s = _extract_series(hourly, "relative_humidity_2m", model, len(times))
        precip_s = _extract_series(hourly, "precipitation", model, len(times))
        snow_s = _extract_series(hourly, "snowfall", model, len(times))
        fl_s = _extract_series(hourly, "freezing_level_height", model, len(times))
        wind_s = _extract_series(hourly, "wind_speed_10m", model, len(times))
        gust_s = _extract_series(hourly, "wind_gusts_10m", model, len(times))

        rows = [
            {
                "time_utc": ts if ts.endswith("Z") else f"{ts}Z",
                "temp_c": temp_s[idx],
                "rh_pct": rh_s[idx],
                "precip_mm": precip_s[idx],
                "snowfall_cm": snow_s[idx],
                "snowfall_in": round(cm_to_inches(snow_s[idx]), 2) if snow_s[idx] is not None else None,
                "freezing_level_m": fl_s[idx],
                "wind_mph": round(kph_to_mph(wind_s[idx]), 1) if wind_s[idx] is not None else None,
                "wind_gust_mph": round(kph_to_mph(gust_s[idx]), 1) if gust_s[idx] is not None else None,
            }
            for idx, ts in enumerate(times)
        ]

        model_results[model] = {"hourly": rows}

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
