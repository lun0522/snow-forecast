"""USDA NRCS SNOTEL AWDB REST adapter for US resorts."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from app.fetchers.snowpack import (
    make_station_record,
    ok_snowpack,
    resort_anchor_coords,
    select_nearest_stations,
    summarize_latest_series,
)
from app.geo import feet_to_meters
from app.http_client import get_json

SNOTEL_STATIONS_URL = "https://wcc.sc.egov.usda.gov/awdbRestApi/services/v1/stations"
SNOTEL_DATA_URL = "https://wcc.sc.egov.usda.gov/awdbRestApi/services/v1/data"
SNOTEL_SOURCE_NAME = "USDA NRCS SNOTEL"

STATE_QUERY_NEIGHBORS: dict[str, tuple[str, ...]] = {
    "CA": ("CA", "NV"),
    "NV": ("NV", "CA"),
}


def parse_snotel_stations(payload: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Normalize SNOTEL station metadata records to common internal coordinates/elevations."""
    stations: list[dict[str, Any]] = []
    for raw in payload or []:
        lat = raw.get("latitude")
        lon = raw.get("longitude")
        elev_ft = raw.get("elevation")
        triplet = raw.get("stationTriplet")
        if lat is None or lon is None or elev_ft is None or not triplet:
            continue
        stations.append(
            {
                "id": str(triplet),
                "name": str(raw.get("name") or triplet),
                "lat": float(lat),
                "lon": float(lon),
                "elevation_m": feet_to_meters(float(elev_ft)),
                "tz_offset_hours": float(raw.get("dataTimeZone") or -8.0),
            }
        )
    return stations


def parse_snotel_data_response(
    payload: list[dict[str, Any]],
    tz_offsets: dict[str, float],
) -> dict[str, dict[str, Any]]:
    """Parse batched AWDB SNWD + WTEQ hourly series keyed by stationTriplet."""
    parsed: dict[str, dict[str, Any]] = {}
    for entry in payload or []:
        triplet = str(entry.get("stationTriplet") or "")
        if not triplet:
            continue
        tz_hours = tz_offsets.get(triplet, -8.0)
        station_tz = timezone(timedelta(hours=tz_hours))

        depth_series: list[tuple[datetime, float]] = []
        swe_series: list[tuple[datetime, float]] = []
        for elem in entry.get("data") or []:
            code = ((elem.get("stationElement") or {}).get("elementCode") or "").upper()
            target = depth_series if code == "SNWD" else swe_series if code == "WTEQ" else None
            if target is None:
                continue
            factor = 2.54 if code == "SNWD" else 25.4
            for pt in elem.get("values") or []:
                val = pt.get("value")
                date_str = pt.get("date")
                if val is None or not date_str:
                    continue
                try:
                    dt_local = datetime.strptime(str(date_str)[:16], "%Y-%m-%d %H:%M").replace(tzinfo=station_tz)
                except ValueError:
                    continue
                target.append((dt_local.astimezone(timezone.utc), float(val) * factor))

        depth_summary = summarize_latest_series(depth_series)
        if depth_summary is None:
            continue
        swe_summary = summarize_latest_series(swe_series) if swe_series else None
        parsed[triplet] = {
            "snow_depth_cm": depth_summary[0],
            "observed_utc": depth_summary[1],
            "delta_24h_cm": depth_summary[2],
            "swe_mm": swe_summary[0] if swe_summary is not None else None,
        }
    return parsed


def fetch_snotel_snowpack_for_resorts(
    resorts: list[dict[str, Any]],
    stations_limit: int = 3,
    max_distance_km: float = 60.0,
    timeout: float = 15.0,
) -> dict[str, dict[str, Any]]:
    """Discover nearby SNOTEL stations dynamically and fetch latest natural snow depth."""
    states: set[str] = set()
    for resort in resorts:
        st = str(resort.get("state") or "").upper()
        if not st:
            continue
        states.update(STATE_QUERY_NEIGHBORS.get(st, (st,)))

    if not states:
        return {}

    station_triplets_param = ",".join(f"*:{s}:SNTL" for s in sorted(states))
    raw_stations = get_json(
        SNOTEL_STATIONS_URL,
        params={"stationTriplets": station_triplets_param, "activeOnly": "true"},
        timeout=timeout,
    )
    stations = parse_snotel_stations(raw_stations)

    candidates_by_resort: dict[str, list[dict[str, Any]]] = {}
    selected_triplets: list[str] = []
    seen_triplets: set[str] = set()
    tz_offsets: dict[str, float] = {}

    for resort in resorts:
        lat, lon = resort_anchor_coords(resort)
        candidates = select_nearest_stations(
            lat=lat,
            lon=lon,
            stations=stations,
            max_distance_km=max_distance_km,
            limit=max(stations_limit + 2, 5),
        )
        candidates_by_resort[resort["id"]] = candidates
        for cand in candidates:
            tid = cand["id"]
            tz_offsets[tid] = float(cand.get("tz_offset_hours", -8.0))
            if tid not in seen_triplets:
                seen_triplets.add(tid)
                selected_triplets.append(tid)

    if not selected_triplets:
        return {r["id"]: ok_snowpack("snotel", SNOTEL_SOURCE_NAME, []) for r in resorts}

    now_utc = datetime.now(timezone.utc)
    begin_str = (now_utc - timedelta(hours=48)).strftime("%Y-%m-%d %H:%M")
    end_str = (now_utc + timedelta(hours=24)).strftime("%Y-%m-%d %H:%M")
    raw_data = get_json(
        SNOTEL_DATA_URL,
        params={
            "stationTriplets": ",".join(selected_triplets),
            "elements": "SNWD,WTEQ",
            "duration": "HOURLY",
            "beginDate": begin_str,
            "endDate": end_str,
        },
        timeout=timeout,
    )
    obs_by_triplet = parse_snotel_data_response(raw_data, tz_offsets=tz_offsets)
    fetched_at = now_utc.isoformat()

    out: dict[str, dict[str, Any]] = {}
    for resort in resorts:
        records: list[dict[str, Any]] = []
        for cand in candidates_by_resort.get(resort["id"], []):
            obs = obs_by_triplet.get(cand["id"])
            if not obs:
                continue
            records.append(
                make_station_record(
                    station=cand,
                    snow_depth_cm=obs["snow_depth_cm"],
                    observed_utc=obs["observed_utc"],
                    delta_24h_cm=obs["delta_24h_cm"],
                    swe_mm=obs["swe_mm"],
                )
            )
            if len(records) >= stations_limit:
                break
        out[resort["id"]] = ok_snowpack("snotel", SNOTEL_SOURCE_NAME, records, fetched_at_utc=fetched_at)
    return out
