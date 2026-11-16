"""BC River Forecast Centre Automated Snow Weather Station (ASWS) CSV adapter."""

from __future__ import annotations

import csv
from datetime import datetime, timezone
from typing import Any

from app.fetchers.snowpack import (
    make_station_record,
    ok_snowpack,
    resort_anchor_coords,
    select_nearest_stations,
    summarize_latest_series,
)
from app.http_client import HttpFetchError, get_json, get_text

BC_ASWS_STATIONS_WFS_URL = (
    "https://openmaps.gov.bc.ca/geo/pub/WHSE_WATER_MANAGEMENT.SSL_SNOW_ASWS_STNS_SP/ows"
)
BC_ASWS_SD_CSV_URL = "https://www.env.gov.bc.ca/wsd/data_searches/snow/asws/data/SD.csv"
BC_ASWS_SW_CSV_URL = "https://www.env.gov.bc.ca/wsd/data_searches/snow/asws/data/SW.csv"
BC_ASWS_SOURCE_NAME = "BC River Forecast Centre ASWS"


def parse_bc_stations_geojson(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Normalize BC ASWS WFS station features to internal coordinates/elevations."""
    stations: list[dict[str, Any]] = []
    for feature in payload.get("features") or []:
        props = feature.get("properties") or {}
        if str(props.get("STATUS") or "").lower() != "active":
            continue
        loc_id = props.get("LOCATION_ID")
        lat = props.get("LATITUDE")
        lon = props.get("LONGITUDE")
        elev_m = props.get("ELEVATION")
        if not loc_id or lat is None or lon is None or elev_m is None:
            continue
        stations.append(
            {
                "id": str(loc_id).strip(),
                "name": str(props.get("LOCATION_NAME") or loc_id).strip(),
                "lat": float(lat),
                "lon": float(lon),
                "elevation_m": float(elev_m),
            }
        )
    return stations


def parse_bc_asws_csv(
    csv_text: str,
    station_ids: set[str],
    tail_rows: int = 96,
) -> dict[str, list[tuple[datetime, float]]]:
    """Extract recent (utc_dt, value) series per station ID from a BC ASWS wide CSV feed."""
    lines = [ln for ln in csv_text.splitlines() if ln.strip()]
    if len(lines) < 2:
        return {}

    header = next(csv.reader([lines[0]]))
    col_map: dict[int, str] = {}
    for idx, col in enumerate(header[1:], start=1):
        token = col.strip().split(" ", 1)[0]
        if token in station_ids:
            col_map[idx] = token

    if not col_map:
        return {}

    recent_lines = lines[1:][-tail_rows:]
    series_by_id: dict[str, list[tuple[datetime, float]]] = {sid: [] for sid in col_map.values()}
    for row in csv.reader(recent_lines):
        if not row:
            continue
        date_str = row[0].strip()
        try:
            dt_utc = datetime.strptime(date_str[:16], "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
        except ValueError:
            continue
        for col_idx, sid in col_map.items():
            if col_idx >= len(row):
                continue
            raw_val = row[col_idx].strip()
            if not raw_val:
                continue
            try:
                series_by_id[sid].append((dt_utc, float(raw_val)))
            except ValueError:
                continue

    return {sid: pts for sid, pts in series_by_id.items() if pts}


def fetch_bc_asws_stations(timeout: float = 20.0) -> list[dict[str, Any]]:
    """Fetch active BC ASWS station metadata from the BC OpenMaps WFS feed."""
    wfs_payload = get_json(
        BC_ASWS_STATIONS_WFS_URL,
        params={
            "service": "WFS",
            "version": "2.0.0",
            "request": "GetFeature",
            "typeNames": "WHSE_WATER_MANAGEMENT.SSL_SNOW_ASWS_STNS_SP",
            "outputFormat": "application/json",
        },
        timeout=timeout,
    )
    return parse_bc_stations_geojson(wfs_payload)


def fetch_bc_asws_snowpack_for_resorts(
    resorts: list[dict[str, Any]],
    stations_limit: int = 3,
    max_distance_km: float = 80.0,
    timeout: float = 20.0,
) -> dict[str, dict[str, Any]]:
    """Read latest BC ASWS SD.csv (and optional SW.csv) using cached or WFS-discovered stations."""
    if not resorts:
        return {}

    discovered_stations: list[dict[str, Any]] = []
    if any(not isinstance(r.get("snowpack_stations"), list) for r in resorts):
        discovered_stations = fetch_bc_asws_stations(timeout=timeout)

    candidates_by_resort: dict[str, list[dict[str, Any]]] = {}
    needed_ids: set[str] = set()
    for resort in resorts:
        lat, lon = resort_anchor_coords(resort)
        cached_pool = resort.get("snowpack_stations")
        pool = cached_pool if isinstance(cached_pool, list) else discovered_stations
        candidates = select_nearest_stations(
            lat=lat,
            lon=lon,
            stations=pool,
            max_distance_km=max_distance_km,
            limit=max(stations_limit + 3, 6),
        )
        candidates_by_resort[resort["id"]] = candidates
        needed_ids.update(str(c["id"]) for c in candidates)

    if not needed_ids:
        return {r["id"]: ok_snowpack("bc_asws", BC_ASWS_SOURCE_NAME, []) for r in resorts}

    sd_csv = get_text(BC_ASWS_SD_CSV_URL, timeout=timeout)
    sd_series = parse_bc_asws_csv(sd_csv, station_ids=needed_ids)

    sw_series: dict[str, list[tuple[datetime, float]]] = {}
    try:
        sw_csv = get_text(BC_ASWS_SW_CSV_URL, timeout=timeout)
        sw_series = parse_bc_asws_csv(sw_csv, station_ids=needed_ids)
    except HttpFetchError:
        pass

    fetched_at = datetime.now(timezone.utc).isoformat()
    out: dict[str, dict[str, Any]] = {}
    for resort in resorts:
        records: list[dict[str, Any]] = []
        for cand in candidates_by_resort.get(resort["id"], []):
            pts = sd_series.get(cand["id"])
            if not pts:
                continue
            sd_summary = summarize_latest_series(pts)
            if sd_summary is None:
                continue
            swe_summary = (
                summarize_latest_series(sw_series[cand["id"]])
                if cand["id"] in sw_series
                else None
            )
            records.append(
                make_station_record(
                    station=cand,
                    snow_depth_cm=sd_summary[0],
                    observed_utc=sd_summary[1],
                    delta_24h_cm=sd_summary[2],
                    swe_mm=swe_summary[0] if swe_summary is not None else None,
                )
            )
            if len(records) >= stations_limit:
                break
        out[resort["id"]] = ok_snowpack("bc_asws", BC_ASWS_SOURCE_NAME, records, fetched_at_utc=fetched_at)
    return out
