"""USDA NRCS AWDB REST API client for SNOTEL station discovery and snow telemetry."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from app.geo import feet_to_meters, haversine_km
from app.http_client import get_json

AWDB_BASE_URL = "https://wcc.sc.egov.usda.gov/awdbRestApi/services/v1"
DEFAULT_ELEMENTS: tuple[str, ...] = ("WTEQ", "SNWD", "PREC", "TOBS")


def fetch_snotel_stations(state_codes: tuple[str, ...] = ("CA", "NV", "UT", "CO")) -> list[dict[str, Any]]:
    """Fetch active SNOTEL station metadata for the given US state codes."""
    stations: list[dict[str, Any]] = []
    for state in state_codes:
        payload = get_json(
            f"{AWDB_BASE_URL}/stations",
            params={
                "stationTriplets": f"*:{state}:SNTL",
                "activeOnly": "true",
            },
        )
        if isinstance(payload, list):
            stations.extend(payload)
    return stations


def find_nearest_snotel_stations(
    lat: float,
    lon: float,
    stations: list[dict[str, Any]],
    limit: int = 3,
    max_distance_km: float = 50.0,
) -> list[dict[str, Any]]:
    """Rank active SNOTEL stations by Haversine distance from a target coordinate."""
    ranked: list[dict[str, Any]] = []
    for st in stations:
        s_lat = st.get("latitude")
        s_lon = st.get("longitude")
        if s_lat is None or s_lon is None:
            continue
        dist_km = haversine_km(lat, lon, float(s_lat), float(s_lon))
        if dist_km > max_distance_km:
            continue
        elev_ft = st.get("elevation")
        ranked.append(
            {
                "triplet": st.get("stationTriplet"),
                "name": st.get("name"),
                "state": st.get("stateCode") or st.get("state"),
                "county": st.get("countyName") or st.get("county"),
                "latitude": float(s_lat),
                "longitude": float(s_lon),
                "elevation_ft": float(elev_ft) if elev_ft is not None else None,
                "elevation_m": round(feet_to_meters(float(elev_ft)), 1) if elev_ft is not None else None,
                "distance_km": round(dist_km, 2),
                "distance_mi": round(dist_km * 0.621371, 2),
            }
        )
    ranked.sort(key=lambda item: item["distance_km"])
    return ranked[:limit]


def parse_snotel_data_response(payload: list[dict[str, Any]]) -> dict[str, Any]:
    """Normalize AWDB /data response into per-station time series and latest telemetry deltas."""
    results: dict[str, Any] = {}
    for station_entry in payload:
        triplet = station_entry.get("stationTriplet")
        if not triplet:
            continue

        by_timestamp: dict[str, dict[str, Any]] = {}
        units: dict[str, str | None] = {}

        for block in station_entry.get("data") or []:
            elem_meta = block.get("stationElement") or {}
            code = elem_meta.get("elementCode")
            if not code:
                continue
            units[code] = elem_meta.get("storedUnitCode")
            for obs in block.get("values") or []:
                ts = obs.get("date")
                if not ts:
                    continue
                row = by_timestamp.setdefault(ts, {"timestamp": ts})
                row[code] = obs.get("value")

        series = [by_timestamp[k] for k in sorted(by_timestamp.keys())]
        summary = _summarize_snotel_series(series)
        results[triplet] = {
            "station_triplet": triplet,
            "units": units,
            "summary": summary,
            "observations": series,
        }
    return results


def _latest_non_null(series: list[dict[str, Any]], key: str) -> tuple[str | None, float | None]:
    for row in reversed(series):
        val = row.get(key)
        if val is not None:
            return row["timestamp"], float(val)
    return None, None


def _value_hours_or_days_ago(
    series: list[dict[str, Any]],
    key: str,
    steps_back: int,
) -> float | None:
    """Return value from N non-null observations before the latest (best-effort delta)."""
    non_null = [float(r[key]) for r in series if r.get(key) is not None]
    if len(non_null) <= steps_back:
        return None
    return non_null[-1 - steps_back]


def _summarize_snotel_series(series: list[dict[str, Any]]) -> dict[str, Any]:
    if not series:
        return {}

    latest_ts, latest_swe = _latest_non_null(series, "WTEQ")
    _, latest_depth = _latest_non_null(series, "SNWD")
    _, latest_temp = _latest_non_null(series, "TOBS")
    _, latest_prec = _latest_non_null(series, "PREC")

    # Detect hourly vs daily cadence from timestamps ("YYYY-MM-DD HH:MM" vs "YYYY-MM-DD")
    is_hourly = any(" " in r["timestamp"] or "T" in r["timestamp"] for r in series)
    step_24h = 24 if is_hourly else 1
    step_48h = 48 if is_hourly else 2

    swe_24h_ago = _value_hours_or_days_ago(series, "WTEQ", step_24h)
    swe_48h_ago = _value_hours_or_days_ago(series, "WTEQ", step_48h)
    depth_24h_ago = _value_hours_or_days_ago(series, "SNWD", step_24h)
    depth_48h_ago = _value_hours_or_days_ago(series, "SNWD", step_48h)

    return {
        "cadence": "HOURLY" if is_hourly else "DAILY",
        "latest_timestamp": latest_ts,
        "swe_in": round(latest_swe, 2) if latest_swe is not None else None,
        "snow_depth_in": round(latest_depth, 1) if latest_depth is not None else None,
        "temp_f": round(latest_temp, 1) if latest_temp is not None else None,
        "precip_accum_in": round(latest_prec, 2) if latest_prec is not None else None,
        "swe_delta_24h_in": (
            round(latest_swe - swe_24h_ago, 2)
            if latest_swe is not None and swe_24h_ago is not None
            else None
        ),
        "swe_delta_48h_in": (
            round(latest_swe - swe_48h_ago, 2)
            if latest_swe is not None and swe_48h_ago is not None
            else None
        ),
        "snow_depth_delta_24h_in": (
            round(latest_depth - depth_24h_ago, 1)
            if latest_depth is not None and depth_24h_ago is not None
            else None
        ),
        "snow_depth_delta_48h_in": (
            round(latest_depth - depth_48h_ago, 1)
            if latest_depth is not None and depth_48h_ago is not None
            else None
        ),
    }


def fetch_snotel_data(
    station_triplets: list[str],
    days_back: int = 7,
    duration: str = "HOURLY",
    elements: tuple[str, ...] = DEFAULT_ELEMENTS,
    end_day: date | None = None,
) -> dict[str, Any]:
    """Fetch recent SNOTEL observations from the USDA NRCS AWDB REST API."""
    if not station_triplets:
        return {}
    anchor = end_day or date.today()
    begin = anchor - timedelta(days=days_back)
    # AWDB treats endDate as 00:00 on that date for HOURLY queries; +1 day captures today's hours.
    query_end = anchor + timedelta(days=1)

    payload = get_json(
        f"{AWDB_BASE_URL}/data",
        params={
            "stationTriplets": ",".join(station_triplets),
            "elements": ",".join(elements),
            "duration": duration,
            "beginDate": begin.isoformat(),
            "endDate": query_end.isoformat(),
        },
    )
    if not isinstance(payload, list):
        return {}
    return parse_snotel_data_response(payload)
