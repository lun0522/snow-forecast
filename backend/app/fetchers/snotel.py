"""USDA NRCS SNOTEL AWDB REST adapter for US resorts."""

from __future__ import annotations

import csv
from datetime import datetime, timedelta, timezone
from typing import Any
import urllib.parse

from app.fetchers.snowpack import (
    make_station_record,
    ok_snowpack,
    resort_anchor_coords,
    select_nearest_stations,
    summarize_latest_series,
)
from app.geo import feet_to_meters
from app.http_client import HttpFetchError, get_json, get_text

SNOTEL_STATIONS_URL = "https://wcc.sc.egov.usda.gov/awdbRestApi/services/v1/stations"
SNOTEL_DATA_URL = "https://wcc.sc.egov.usda.gov/awdbRestApi/services/v1/data"
SNOTEL_REPORT_CSV_URL_TEMPLATE = (
    "https://wcc.sc.egov.usda.gov/reportGenerator/view_csv/"
    "customSingleStationReport/hourly/{triplet}%7Cid=%22%22%7Cname/-48,0/SNWD::value,WTEQ::value"
)
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


def _summarize_station_series(
    depth_series: list[tuple[datetime, float]],
    swe_series: list[tuple[datetime, float]],
) -> dict[str, Any] | None:
    """Summarize parsed depth (cm) and optional SWE (mm) series into a station observation."""
    depth_summary = summarize_latest_series(depth_series)
    if depth_summary is None:
        return None
    swe_summary = summarize_latest_series(swe_series) if swe_series else None
    return {
        "snow_depth_cm": depth_summary[0],
        "observed_utc": depth_summary[1],
        "delta_24h_cm": depth_summary[2],
        "swe_mm": swe_summary[0] if swe_summary is not None else None,
    }


def _parse_local_timestamp(date_str: str, station_tz: timezone) -> datetime | None:
    try:
        dt_local = datetime.strptime(str(date_str).strip()[:16], "%Y-%m-%d %H:%M")
    except ValueError:
        return None
    return dt_local.replace(tzinfo=station_tz).astimezone(timezone.utc)


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
        station_tz = timezone(timedelta(hours=tz_offsets.get(triplet, -8.0)))

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
                dt_utc = _parse_local_timestamp(str(date_str), station_tz)
                if dt_utc is None:
                    continue
                target.append((dt_utc, float(val) * factor))

        summary = _summarize_station_series(depth_series, swe_series)
        if summary is not None:
            parsed[triplet] = summary
    return parsed


def parse_snotel_report_csv(
    csv_text: str,
    tz_offset_hours: float = -8.0,
) -> dict[str, Any] | None:
    """Parse USDA reportGenerator hourly CSV output for a single SNOTEL station."""
    lines = [ln for ln in csv_text.splitlines() if ln.strip() and not ln.lstrip().startswith("#")]
    if len(lines) < 2:
        return None

    header = next(csv.reader([lines[0]]))
    date_idx: int | None = None
    snwd_idx: int | None = None
    wteq_idx: int | None = None
    for idx, col in enumerate(header):
        norm = col.strip().lower()
        if norm == "date":
            date_idx = idx
        elif "snow depth" in norm:
            snwd_idx = idx
        elif "snow water equivalent" in norm:
            wteq_idx = idx

    if date_idx is None or snwd_idx is None:
        return None

    station_tz = timezone(timedelta(hours=tz_offset_hours))
    depth_series: list[tuple[datetime, float]] = []
    swe_series: list[tuple[datetime, float]] = []

    for row in csv.reader(lines[1:]):
        if len(row) <= date_idx:
            continue
        dt_utc = _parse_local_timestamp(row[date_idx], station_tz)
        if dt_utc is None:
            continue
        if snwd_idx < len(row) and row[snwd_idx].strip():
            try:
                depth_series.append((dt_utc, float(row[snwd_idx].strip()) * 2.54))
            except ValueError:
                pass
        if wteq_idx is not None and wteq_idx < len(row) and row[wteq_idx].strip():
            try:
                swe_series.append((dt_utc, float(row[wteq_idx].strip()) * 25.4))
            except ValueError:
                pass

    return _summarize_station_series(depth_series, swe_series)


def fetch_snotel_stations_for_states(
    states: set[str],
    timeout: float = 15.0,
) -> list[dict[str, Any]]:
    """Fetch active SNOTEL station metadata for states, falling back per-state if needed."""
    sorted_states = sorted({s.upper() for s in states if s})
    if not sorted_states:
        return []

    station_triplets_param = ",".join(f"*:{s}:SNTL" for s in sorted_states)
    try:
        raw_stations = get_json(
            SNOTEL_STATIONS_URL,
            params={"stationTriplets": station_triplets_param, "activeOnly": "true"},
            timeout=timeout,
        )
        return parse_snotel_stations(raw_stations)
    except HttpFetchError as exc:
        if len(sorted_states) == 1:
            raise
        combined: dict[str, dict[str, Any]] = {}
        last_err: HttpFetchError = exc
        for state in sorted_states:
            try:
                raw_state = get_json(
                    SNOTEL_STATIONS_URL,
                    params={"stationTriplets": f"*:{state}:SNTL", "activeOnly": "true"},
                    timeout=timeout,
                )
            except HttpFetchError as state_exc:
                last_err = state_exc
                continue
            for station in parse_snotel_stations(raw_state):
                combined[station["id"]] = station
        if not combined:
            raise last_err
        return list(combined.values())


def _fetch_observations_via_report_generator(
    resorts: list[dict[str, Any]],
    candidates_by_resort: dict[str, list[dict[str, Any]]],
    stations_limit: int,
    tz_offsets: dict[str, float],
    timeout: float,
) -> dict[str, dict[str, Any]]:
    """Fallback per-station hourly fetch via USDA reportGenerator CSV when awdbRestApi fails."""
    obs_cache: dict[str, dict[str, Any] | None] = {}
    consecutive_errors = 0
    any_success = False
    last_error: HttpFetchError | None = None

    for resort in resorts:
        valid_for_resort = 0
        for cand in candidates_by_resort.get(resort["id"], []):
            tid = str(cand["id"])
            if tid not in obs_cache:
                if consecutive_errors >= 3 and not any_success:
                    break
                url = SNOTEL_REPORT_CSV_URL_TEMPLATE.format(
                    triplet=urllib.parse.quote(tid, safe=":")
                )
                try:
                    csv_text = get_text(url, timeout=min(timeout, 10.0), retries=2)
                    consecutive_errors = 0
                    parsed = parse_snotel_report_csv(
                        csv_text,
                        tz_offset_hours=tz_offsets.get(tid, -8.0),
                    )
                    obs_cache[tid] = parsed
                    if parsed is not None:
                        any_success = True
                except HttpFetchError as exc:
                    consecutive_errors += 1
                    last_error = exc
                    obs_cache[tid] = None

            if obs_cache.get(tid) is not None:
                valid_for_resort += 1
                if valid_for_resort >= stations_limit:
                    break

    if not any_success and last_error is not None:
        raise last_error
    return {tid: obs for tid, obs in obs_cache.items() if obs is not None}


def fetch_snotel_snowpack_for_resorts(
    resorts: list[dict[str, Any]],
    stations_limit: int = 3,
    max_distance_km: float = 60.0,
    timeout: float = 15.0,
) -> dict[str, dict[str, Any]]:
    """Fetch latest natural snow depth using cached or dynamically discovered SNOTEL stations."""
    if not resorts:
        return {}

    discovered_stations: list[dict[str, Any]] = []
    resorts_needing_discovery = [
        r for r in resorts if not isinstance(r.get("snowpack_stations"), list)
    ]
    if resorts_needing_discovery:
        states: set[str] = set()
        for resort in resorts_needing_discovery:
            st = str(resort.get("state") or "").upper()
            if st:
                states.update(STATE_QUERY_NEIGHBORS.get(st, (st,)))
        if states:
            discovered_stations = fetch_snotel_stations_for_states(states, timeout=timeout)

    candidates_by_resort: dict[str, list[dict[str, Any]]] = {}
    selected_triplets: list[str] = []
    seen_triplets: set[str] = set()
    tz_offsets: dict[str, float] = {}

    for resort in resorts:
        lat, lon = resort_anchor_coords(resort)
        cached_pool = resort.get("snowpack_stations")
        pool = cached_pool if isinstance(cached_pool, list) else discovered_stations
        candidates = select_nearest_stations(
            lat=lat,
            lon=lon,
            stations=pool,
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
    try:
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
    except HttpFetchError as exc:
        print(f"[warn] SNOTEL AWDB /data unavailable ({exc}); falling back to reportGenerator CSV.")
        obs_by_triplet = _fetch_observations_via_report_generator(
            resorts=resorts,
            candidates_by_resort=candidates_by_resort,
            stations_limit=stations_limit,
            tz_offsets=tz_offsets,
            timeout=timeout,
        )

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
