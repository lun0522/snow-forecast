"""Unified interface and shared station-matching helpers for natural snowpack telemetry."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from app.geo import cm_to_inches, haversine_km, meters_to_feet, mm_to_inches
from app.http_client import HttpFetchError

SNOWPACK_LABEL = "Nearby Snow Telemetry (Natural)"
CANADIAN_PROVINCES = frozenset({"BC", "AB", "ON", "QC", "YT"})


def resort_anchor_coords(resort: dict[str, Any]) -> tuple[float, float]:
    """Return representative resort coordinates (mid band preferred) for station matching."""
    bands = resort.get("bands") or {}
    band = bands.get("mid") or bands.get("summit") or bands.get("base")
    if not band:
        raise ValueError(f"Resort {resort.get('id')} has no bands defined")
    return float(band["lat"]), float(band["lon"])


def select_nearest_stations(
    lat: float,
    lon: float,
    stations: list[dict[str, Any]],
    max_distance_km: float = 75.0,
    limit: int = 5,
) -> list[dict[str, Any]]:
    """Return nearest candidate stations sorted by great-circle distance within max_distance_km."""
    ranked: list[dict[str, Any]] = []
    for st in stations:
        st_lat = st.get("lat")
        st_lon = st.get("lon")
        if st_lat is None or st_lon is None:
            continue
        dist = haversine_km(lat, lon, float(st_lat), float(st_lon))
        if dist <= max_distance_km:
            ranked.append({**st, "distance_km": round(dist, 1)})
    ranked.sort(key=lambda s: float(s["distance_km"]))
    return ranked[:limit]


def summarize_latest_series(
    series: list[tuple[datetime, float]],
) -> tuple[float, datetime, float | None] | None:
    """Return (latest_val, observed_utc, delta_24h) from valid (utc_dt, value) samples."""
    clean = sorted(
        [(dt.astimezone(timezone.utc), max(0.0, float(val))) for dt, val in series if val is not None and val >= -5.0],
        key=lambda item: item[0],
    )
    if not clean:
        return None
    latest_dt, latest_cm = clean[-1]
    target_past = latest_dt - timedelta(hours=24)
    best_past: tuple[float, float] | None = None
    for dt, val in clean[:-1]:
        offset_sec = abs((dt - target_past).total_seconds())
        if offset_sec <= 6 * 3600:
            if best_past is None or offset_sec < best_past[0]:
                best_past = (offset_sec, val)
    delta_24h = round(latest_cm - best_past[1], 1) if best_past is not None else None
    return round(latest_cm, 1), latest_dt, delta_24h


def make_station_record(
    station: dict[str, Any],
    snow_depth_cm: float,
    observed_utc: datetime,
    delta_24h_cm: float | None = None,
    swe_mm: float | None = None,
) -> dict[str, Any]:
    """Normalize a single snowpack station observation to the shared snowpack schema."""
    elev_m = float(station["elevation_m"])
    clean_cm = round(max(0.0, float(snow_depth_cm)), 1)
    clean_swe_mm = round(max(0.0, float(swe_mm)), 1) if swe_mm is not None else None
    return {
        "id": str(station["id"]),
        "name": str(station["name"]),
        "elevation_m": round(elev_m, 1),
        "elevation_ft": round(meters_to_feet(elev_m)),
        "distance_km": round(float(station["distance_km"]), 1),
        "snow_depth_cm": clean_cm,
        "snow_depth_in": round(cm_to_inches(clean_cm), 1),
        "swe_mm": clean_swe_mm,
        "swe_in": round(mm_to_inches(clean_swe_mm), 2) if clean_swe_mm is not None else None,
        "delta_24h_cm": delta_24h_cm,
        "observed_at_utc": observed_utc.astimezone(timezone.utc).isoformat(),
    }


def ok_snowpack(
    network: str,
    source_name: str,
    stations: list[dict[str, Any]],
    fetched_at_utc: str | None = None,
) -> dict[str, Any]:
    """Construct a successful unified current_snowpack payload."""
    return {
        "status": "ok" if stations else "unavailable",
        "label": SNOWPACK_LABEL,
        "network": network,
        "source_name": source_name,
        "fetched_at_utc": fetched_at_utc or datetime.now(timezone.utc).isoformat(),
        "stations": stations,
        **({"error": "No nearby reporting stations with active snow depth sensors"} if not stations else {}),
    }


def unavailable_snowpack(network: str, source_name: str, error: str) -> dict[str, Any]:
    """Construct a fallback unavailable current_snowpack payload."""
    return {
        "status": "unavailable",
        "label": SNOWPACK_LABEL,
        "network": network,
        "source_name": source_name,
        "fetched_at_utc": datetime.now(timezone.utc).isoformat(),
        "stations": [],
        "error": error,
    }


def fetch_current_snowpack_for_resorts(resorts: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Fetch natural snowpack telemetry per resort using regional station adapters."""
    from app.fetchers.bc_asws import BC_ASWS_SOURCE_NAME, fetch_bc_asws_snowpack_for_resorts
    from app.fetchers.snotel import SNOTEL_SOURCE_NAME, fetch_snotel_snowpack_for_resorts

    results: dict[str, dict[str, Any]] = {}
    us_resorts = [r for r in resorts if str(r.get("state") or "").upper() not in CANADIAN_PROVINCES]
    bc_resorts = [r for r in resorts if str(r.get("state") or "").upper() == "BC"]
    other_resorts = [
        r for r in resorts if r not in us_resorts and r not in bc_resorts
    ]

    if us_resorts:
        try:
            results.update(fetch_snotel_snowpack_for_resorts(us_resorts))
        except HttpFetchError as exc:
            for r in us_resorts:
                results[r["id"]] = unavailable_snowpack("snotel", SNOTEL_SOURCE_NAME, str(exc))

    if bc_resorts:
        try:
            results.update(fetch_bc_asws_snowpack_for_resorts(bc_resorts))
        except HttpFetchError as exc:
            for r in bc_resorts:
                results[r["id"]] = unavailable_snowpack("bc_asws", BC_ASWS_SOURCE_NAME, str(exc))

    for r in other_resorts:
        results[r["id"]] = unavailable_snowpack(
            "none",
            "Regional Telemetry",
            f"No natural snowpack telemetry adapter configured for region '{r.get('state')}'",
        )

    return results
