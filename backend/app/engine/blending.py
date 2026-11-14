"""Timeline normalization and multi-model consensus blending engine."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from statistics import median
from typing import Any
from zoneinfo import ZoneInfo

from app.engine.physics import (
    apply_snowpack_settling,
    classify_snow_fraction,
    compute_hourly_physics_snow,
    estimate_snow_level_m,
)
from app.geo import c_to_f, kph_to_mph, meters_to_feet, mm_to_inches
from app.time_utils import floor_utc_hour, parse_utc

HORIZON_HOURS = 168
STANDARD_WINDOWS_HOURS = (24, 48, 72, 120, 168)

MODEL_DISPLAY_NAMES: dict[str, str] = {
    "ecmwf_ifs025": "ECMWF IFS (25km)",
    "gfs_global": "NOAA GFS (13-25km)",
    "gfs_hrrr": "NOAA HRRR (3km)",
    "ncep_nbm_conus": "NCEP NBM (2.5km)",
    "gem_global": "CMC GEM (15km)",
    "icon_global": "DWD ICON (11km)",
    "met_no": "MET Norway / ECMWF (9km)",
    "nws_gridpoints": "NWS NDFD Gridpoints (2.5km)",
}


def _quantile(sorted_vals: list[float], q: float) -> float:
    if not sorted_vals:
        return 0.0
    if len(sorted_vals) == 1:
        return sorted_vals[0]
    pos = q * (len(sorted_vals) - 1)
    lo = int(pos)
    hi = min(lo + 1, len(sorted_vals) - 1)
    frac = pos - lo
    return sorted_vals[lo] * (1.0 - frac) + sorted_vals[hi] * frac


def _score_confidence(
    model_snow_totals: list[float],
    rain_snow_risk: str,
    total_precip_in: float,
) -> tuple[str, int]:
    """Derive qualitative and numeric forecast confidence from multi-model agreement and phase risk."""
    if len(model_snow_totals) < 2:
        return ("low", 35)

    ordered = sorted(model_snow_totals)
    med = median(ordered)
    spread = ordered[-1] - ordered[0]
    iqr = _quantile(ordered, 0.75) - _quantile(ordered, 0.25)

    if med < 0.5 and ordered[-1] < 1.0:
        score = 90.0
    else:
        denom = max(med, 3.0)
        rel_iqr = iqr / denom
        rel_spread = spread / denom
        penalty = min(55.0, rel_iqr * 45.0 + max(0.0, rel_spread - 0.5) * 15.0)
        score = 90.0 - penalty

    if total_precip_in >= 0.15 and rain_snow_risk == "mixed":
        score -= 12.0

    clamped = int(round(max(20.0, min(95.0, score))))
    if clamped >= 72:
        label = "high"
    elif clamped >= 48:
        label = "medium"
    else:
        label = "low"
    return (label, clamped)


def _blank_hourly_slot(hour_dt: datetime) -> dict[str, Any]:
    return {
        "time_utc": hour_dt.isoformat(),
        "covered": False,
        "precip_mm": 0.0,
        "native_snow_in": 0.0,
        "temp_c": None,
        "rh_pct": None,
        "wind_mph": None,
        "wind_gust_mph": None,
        "freezing_level_m": None,
        "snow_level_m": None,
    }


def _build_physics_series(
    raw_slots: list[dict[str, Any]],
    band_elevation_m: float | None,
) -> list[dict[str, Any]]:
    """Run Step 3 snow physics & compaction on an aligned hourly slot list."""
    enriched: list[dict[str, Any]] = []
    hourly_snow: list[float] = []
    hourly_temp: list[float | None] = []
    hourly_wind: list[float | None] = []

    for slot in raw_slots:
        if not slot["covered"]:
            enriched.append(
                {
                    "time_utc": slot["time_utc"],
                    "covered": False,
                    "precip_in": None,
                    "native_snow_in": None,
                    "physics_snow_in": None,
                    "settled_snow_in": None,
                    "snow_fraction": None,
                    "slr": None,
                    "temp_f": None,
                    "wet_bulb_f": None,
                    "wind_mph": None,
                    "wind_gust_mph": None,
                    "snow_level_ft": None,
                }
            )
            hourly_snow.append(0.0)
            hourly_temp.append(None)
            hourly_wind.append(None)
            continue

        phys = compute_hourly_physics_snow(
            precip_mm=slot["precip_mm"],
            temp_c=slot["temp_c"],
            rh_pct=slot["rh_pct"],
            wind_mph=slot["wind_mph"],
            band_elevation_m=band_elevation_m,
            freezing_level_m=slot["freezing_level_m"],
            snow_level_m=slot["snow_level_m"],
        )
        eff_snow_lvl_m = estimate_snow_level_m(
            freezing_level_m=slot["freezing_level_m"],
            snow_level_m=slot["snow_level_m"],
        )
        wet_bulb_c = phys["wet_bulb_c"]

        row = {
            "time_utc": slot["time_utc"],
            "covered": True,
            "precip_in": round(mm_to_inches(slot["precip_mm"]), 3),
            "native_snow_in": round(slot["native_snow_in"], 3),
            "physics_snow_in": round(float(phys["physics_snow_in"]), 3),
            "settled_snow_in": None,
            "snow_fraction": phys["snow_fraction"],
            "slr": phys["slr"],
            "temp_f": round(c_to_f(slot["temp_c"]), 1) if slot["temp_c"] is not None else None,
            "wet_bulb_f": round(c_to_f(wet_bulb_c), 1) if wet_bulb_c is not None else None,
            "wind_mph": round(slot["wind_mph"], 1) if slot["wind_mph"] is not None else None,
            "wind_gust_mph": (
                round(slot["wind_gust_mph"], 1) if slot["wind_gust_mph"] is not None else None
            ),
            "snow_level_ft": round(meters_to_feet(eff_snow_lvl_m)) if eff_snow_lvl_m is not None else None,
        }
        enriched.append(row)
        hourly_snow.append(float(phys["physics_snow_in"] or 0.0))
        hourly_temp.append(slot["temp_c"])
        hourly_wind.append(slot["wind_mph"])

    settled = apply_snowpack_settling(hourly_snow, hourly_temp, hourly_wind)
    for row, settled_val in zip(enriched, settled):
        if row["covered"]:
            row["settled_snow_in"] = settled_val

    return enriched


def _normalize_open_meteo_model(
    rows: list[dict[str, Any]],
    anchor_utc: datetime,
    horizon_hours: int,
    band_elevation_m: float | None,
) -> list[dict[str, Any]]:
    grid = [_blank_hourly_slot(anchor_utc + timedelta(hours=i)) for i in range(horizon_hours)]
    by_idx: dict[int, dict[str, Any]] = {}
    for row in rows:
        has_data = (
            row.get("temp_c") is not None
            or row.get("precip_mm") is not None
            or row.get("snowfall_cm") is not None
        )
        if not has_data:
            continue
        t = parse_utc(row["time_utc"])
        idx = int(round((t - anchor_utc).total_seconds() / 3600.0))
        if 0 <= idx < horizon_hours:
            by_idx[idx] = row

    for idx, slot in enumerate(grid):
        src = by_idx.get(idx)
        if not src:
            continue
        slot["covered"] = True
        slot["precip_mm"] = float(src.get("precip_mm") or 0.0)
        slot["native_snow_in"] = float(src.get("snowfall_in") or 0.0)
        slot["temp_c"] = src.get("temp_c")
        slot["rh_pct"] = src.get("rh_pct")
        slot["wind_mph"] = src.get("wind_mph")
        slot["wind_gust_mph"] = src.get("wind_gust_mph")
        slot["freezing_level_m"] = src.get("freezing_level_m")

    return _build_physics_series(grid, band_elevation_m)


def _preparse_entries(entries: list[dict[str, Any]]) -> list[tuple[datetime, datetime, float, Any]]:
    parsed: list[tuple[datetime, datetime, float, Any]] = []
    for entry in entries:
        e_start = parse_utc(entry["start_utc"])
        e_end = parse_utc(entry["end_utc"])
        span = (e_end - e_start).total_seconds()
        if span > 0:
            parsed.append((e_start, e_end, span, entry.get("value")))
    return parsed


def _pick_interval_value(
    parsed_entries: list[tuple[datetime, datetime, float, Any]],
    h_start: datetime,
    h_end: datetime,
) -> float | None:
    """Return value from the narrowest interval overlapping hour [h_start, h_end)."""
    best_span: float | None = None
    best_val: float | None = None
    for e_start, e_end, span, val in parsed_entries:
        if e_end <= h_start or e_start >= h_end:
            continue
        if best_span is None or span < best_span:
            best_span = span
            best_val = val
    return best_val


def _normalize_met_no(
    met_data: dict[str, Any],
    anchor_utc: datetime,
    horizon_hours: int,
    band_elevation_m: float | None,
) -> list[dict[str, Any]]:
    grid = [_blank_hourly_slot(anchor_utc + timedelta(hours=i)) for i in range(horizon_hours)]
    intervals = met_data.get("intervals") or []
    best_state_span: list[float | None] = [None] * horizon_hours

    for iv in intervals:
        e_start = parse_utc(iv["start_utc"])
        e_end = parse_utc(iv["end_utc"])
        dur_sec = (e_end - e_start).total_seconds()
        if dur_sec <= 0:
            continue

        start_idx = max(0, int((e_start - anchor_utc).total_seconds() // 3600))
        end_idx = min(horizon_hours - 1, int(((e_end - timedelta(seconds=1)) - anchor_utc).total_seconds() // 3600))
        for idx in range(start_idx, end_idx + 1):
            h_start = anchor_utc + timedelta(hours=idx)
            h_end = h_start + timedelta(hours=1)
            ov_start = max(e_start, h_start)
            ov_end = min(e_end, h_end)
            if ov_end <= ov_start:
                continue

            frac = (ov_end - ov_start).total_seconds() / dur_sec
            slot = grid[idx]
            slot["covered"] = True
            if iv.get("precip_mm") is not None:
                slot["precip_mm"] += float(iv["precip_mm"]) * frac
            if iv.get("est_snow_in") is not None:
                slot["native_snow_in"] += float(iv["est_snow_in"]) * frac

            if best_state_span[idx] is None or dur_sec < best_state_span[idx]:  # type: ignore[operator]
                best_state_span[idx] = dur_sec
                slot["temp_c"] = iv.get("temp_c")
                slot["rh_pct"] = iv.get("rh_pct")
                slot["wind_mph"] = iv.get("wind_mph")
                slot["wind_gust_mph"] = iv.get("wind_gust_mph")

    return _build_physics_series(grid, band_elevation_m)


def _distribute_nws_accum(
    entries: list[dict[str, Any]],
    anchor_utc: datetime,
    horizon_hours: int,
) -> tuple[list[float], list[bool]]:
    totals = [0.0] * horizon_hours
    has_data = [False] * horizon_hours
    for entry in entries:
        e_start = parse_utc(entry["start_utc"])
        e_end = parse_utc(entry["end_utc"])
        dur_sec = (e_end - e_start).total_seconds()
        if dur_sec <= 0:
            continue
        start_idx = max(0, int((e_start - anchor_utc).total_seconds() // 3600))
        end_idx = min(horizon_hours - 1, int(((e_end - timedelta(seconds=1)) - anchor_utc).total_seconds() // 3600))
        for idx in range(start_idx, end_idx + 1):
            h_start = anchor_utc + timedelta(hours=idx)
            h_end = h_start + timedelta(hours=1)
            ov_start = max(e_start, h_start)
            ov_end = min(e_end, h_end)
            if ov_end > ov_start:
                frac = (ov_end - ov_start).total_seconds() / dur_sec
                totals[idx] += float(entry["value"]) * frac
                has_data[idx] = True
    return totals, has_data


def _normalize_nws(
    nws_data: dict[str, Any],
    anchor_utc: datetime,
    horizon_hours: int,
    band_elevation_m: float | None,
) -> list[dict[str, Any]]:
    grid = [_blank_hourly_slot(anchor_utc + timedelta(hours=i)) for i in range(horizon_hours)]
    layers = nws_data.get("layers") or {}

    qpf_vals, qpf_cov = _distribute_nws_accum(
        layers.get("quantitative_precipitation_mm") or [], anchor_utc, horizon_hours
    )
    snow_vals, snow_cov = _distribute_nws_accum(
        layers.get("snowfall_amount_mm") or [], anchor_utc, horizon_hours
    )

    temp_entries = _preparse_entries(layers.get("temperature_c") or [])
    snow_lvl_entries = _preparse_entries(layers.get("snow_level_m") or [])
    wind_entries = _preparse_entries(layers.get("wind_speed_kph") or [])
    gust_entries = _preparse_entries(layers.get("wind_gust_kph") or [])

    for idx, slot in enumerate(grid):
        h_start = anchor_utc + timedelta(hours=idx)
        h_end = h_start + timedelta(hours=1)
        temp_c = _pick_interval_value(temp_entries, h_start, h_end)
        snow_lvl_m = _pick_interval_value(snow_lvl_entries, h_start, h_end)
        wind_kph = _pick_interval_value(wind_entries, h_start, h_end)
        gust_kph = _pick_interval_value(gust_entries, h_start, h_end)

        if qpf_cov[idx] or snow_cov[idx] or temp_c is not None:
            slot["covered"] = True
            slot["precip_mm"] = qpf_vals[idx]
            slot["native_snow_in"] = mm_to_inches(snow_vals[idx])
            slot["temp_c"] = temp_c
            slot["snow_level_m"] = snow_lvl_m
            slot["wind_mph"] = kph_to_mph(wind_kph) if wind_kph is not None else None
            slot["wind_gust_mph"] = kph_to_mph(gust_kph) if gust_kph is not None else None

    return _build_physics_series(grid, band_elevation_m)


def _summarize_model_slice(rows: list[dict[str, Any]]) -> dict[str, Any]:
    covered = [r for r in rows if r["covered"]]
    snow_total = sum(float(r["physics_snow_in"] or 0.0) for r in covered)
    native_total = sum(float(r["native_snow_in"] or 0.0) for r in covered)
    precip_total = sum(float(r["precip_in"] or 0.0) for r in covered)
    temps = [r["temp_f"] for r in covered if r["temp_f"] is not None]
    winds = [r["wind_mph"] for r in covered if r["wind_mph"] is not None]
    gusts = [r["wind_gust_mph"] for r in covered if r["wind_gust_mph"] is not None]
    snow_lvls = [r["snow_level_ft"] for r in covered if r["snow_level_ft"] is not None]
    settled_vals = [r["settled_snow_in"] for r in covered if r["settled_snow_in"] is not None]

    # Precip-weighted SLR & snow fraction when precip occurs, otherwise mean over covered hours
    precip_hours = [r for r in covered if (r["precip_in"] or 0.0) > 0.005]
    if precip_hours:
        w_sum = sum(float(r["precip_in"] or 0.0) for r in precip_hours)
        avg_slr = sum(float(r["slr"] or 10.0) * float(r["precip_in"] or 0.0) for r in precip_hours) / w_sum
        avg_frac = (
            sum(float(r["snow_fraction"] or 0.0) * float(r["precip_in"] or 0.0) for r in precip_hours) / w_sum
        )
    elif covered:
        slrs = [float(r["slr"]) for r in covered if r["slr"] is not None]
        fracs = [float(r["snow_fraction"]) for r in covered if r["snow_fraction"] is not None]
        avg_slr = sum(slrs) / len(slrs) if slrs else 10.0
        avg_frac = sum(fracs) / len(fracs) if fracs else 0.5
    else:
        avg_slr = 10.0
        avg_frac = 0.5

    return {
        "covered_hours": len(covered),
        "physics_snow_in": round(snow_total, 2),
        "native_snow_in": round(native_total, 2),
        "precip_in": round(precip_total, 2),
        "settled_peak_in": round(max(settled_vals), 2) if settled_vals else 0.0,
        "avg_slr": round(avg_slr, 1),
        "snow_fraction": round(avg_frac, 2),
        "rain_snow_risk": classify_snow_fraction(avg_frac),
        "temp_min_f": round(min(temps), 1) if temps else None,
        "temp_max_f": round(max(temps), 1) if temps else None,
        "max_wind_mph": round(max(winds), 1) if winds else None,
        "max_gust_mph": round(max(gusts), 1) if gusts else None,
        "snow_level_min_ft": round(min(snow_lvls)) if snow_lvls else None,
        "snow_level_max_ft": round(max(snow_lvls)) if snow_lvls else None,
    }


def _aggregate_consensus_slice(
    indices: list[int],
    model_series: dict[str, list[dict[str, Any]]],
    min_coverage_ratio: float = 0.85,
) -> dict[str, Any]:
    """Compute cross-model consensus statistics over a set of hour indices (window or local day)."""
    if not indices:
        return {
            "snow_min_in": 0.0,
            "snow_median_in": 0.0,
            "snow_max_in": 0.0,
            "native_snow_median_in": 0.0,
            "precip_median_in": 0.0,
            "avg_slr": 10.0,
            "snow_fraction": 0.5,
            "rain_snow_risk": "mixed",
            "temp_min_f": None,
            "temp_max_f": None,
            "max_wind_mph": None,
            "max_gust_mph": None,
            "snow_level_min_ft": None,
            "snow_level_max_ft": None,
            "model_count": 0,
            "models_used": [],
            "confidence": "low",
            "confidence_score": 20,
        }

    req_hours = max(1, int(round(len(indices) * min_coverage_ratio)))
    eligible_models: dict[str, dict[str, Any]] = {}

    for model_id, rows in model_series.items():
        subset = [rows[i] for i in indices if 0 <= i < len(rows)]
        summary = _summarize_model_slice(subset)
        if summary["covered_hours"] >= req_hours:
            eligible_models[model_id] = summary

    # Fall back to whatever models cover at least 50% if no model hit 85%
    if not eligible_models:
        fallback_req = max(1, len(indices) // 2)
        for model_id, rows in model_series.items():
            subset = [rows[i] for i in indices if 0 <= i < len(rows)]
            summary = _summarize_model_slice(subset)
            if summary["covered_hours"] >= fallback_req:
                eligible_models[model_id] = summary

    if not eligible_models:
        return {
            "snow_min_in": 0.0,
            "snow_median_in": 0.0,
            "snow_max_in": 0.0,
            "native_snow_median_in": 0.0,
            "precip_median_in": 0.0,
            "avg_slr": 10.0,
            "snow_fraction": 0.5,
            "rain_snow_risk": "mixed",
            "temp_min_f": None,
            "temp_max_f": None,
            "max_wind_mph": None,
            "max_gust_mph": None,
            "snow_level_min_ft": None,
            "snow_level_max_ft": None,
            "model_count": 0,
            "models_used": [],
            "confidence": "low",
            "confidence_score": 20,
        }

    vals = list(eligible_models.values())
    snows = [v["physics_snow_in"] for v in vals]
    natives = [v["native_snow_in"] for v in vals]
    precips = [v["precip_in"] for v in vals]
    slrs = [v["avg_slr"] for v in vals]
    fracs = [v["snow_fraction"] for v in vals]
    t_mins = [v["temp_min_f"] for v in vals if v["temp_min_f"] is not None]
    t_maxs = [v["temp_max_f"] for v in vals if v["temp_max_f"] is not None]
    winds = [v["max_wind_mph"] for v in vals if v["max_wind_mph"] is not None]
    gusts = [v["max_gust_mph"] for v in vals if v["max_gust_mph"] is not None]
    sl_mins = [v["snow_level_min_ft"] for v in vals if v["snow_level_min_ft"] is not None]
    sl_maxs = [v["snow_level_max_ft"] for v in vals if v["snow_level_max_ft"] is not None]

    med_frac = median(fracs)
    med_precip = median(precips)
    risk = classify_snow_fraction(med_frac)
    conf_label, conf_score = _score_confidence(snows, risk, med_precip)

    return {
        "snow_min_in": round(min(snows), 2),
        "snow_median_in": round(median(snows), 2),
        "snow_max_in": round(max(snows), 2),
        "native_snow_median_in": round(median(natives), 2),
        "precip_median_in": round(med_precip, 2),
        "avg_slr": round(median(slrs), 1),
        "snow_fraction": round(med_frac, 2),
        "rain_snow_risk": risk,
        "temp_min_f": round(min(t_mins), 1) if t_mins else None,
        "temp_max_f": round(max(t_maxs), 1) if t_maxs else None,
        "max_wind_mph": round(median(winds), 1) if winds else None,
        "max_gust_mph": round(median(gusts), 1) if gusts else None,
        "snow_level_min_ft": round(median(sl_mins)) if sl_mins else None,
        "snow_level_max_ft": round(median(sl_maxs)) if sl_maxs else None,
        "model_count": len(eligible_models),
        "models_used": sorted(eligible_models.keys()),
        "confidence": conf_label,
        "confidence_score": conf_score,
    }


def _build_consensus_hourly(
    model_series: dict[str, list[dict[str, Any]]],
    anchor_utc: datetime,
    horizon_hours: int,
    local_tz: ZoneInfo,
) -> list[dict[str, Any]]:
    timeline: list[dict[str, Any]] = []
    hourly_med_snow: list[float] = []
    hourly_med_temp_c: list[float | None] = []
    hourly_med_wind_mph: list[float | None] = []

    for idx in range(horizon_hours):
        h_utc = anchor_utc + timedelta(hours=idx)
        active = [rows[idx] for rows in model_series.values() if idx < len(rows) and rows[idx]["covered"]]

        snows = [float(r["physics_snow_in"] or 0.0) for r in active]
        precips = [float(r["precip_in"] or 0.0) for r in active]
        temps_f = [float(r["temp_f"]) for r in active if r["temp_f"] is not None]
        winds = [float(r["wind_mph"]) for r in active if r["wind_mph"] is not None]
        gusts = [float(r["wind_gust_mph"]) for r in active if r["wind_gust_mph"] is not None]
        snow_lvls = [int(r["snow_level_ft"]) for r in active if r["snow_level_ft"] is not None]
        slrs = [float(r["slr"]) for r in active if r["slr"] is not None]
        fracs = [float(r["snow_fraction"]) for r in active if r["snow_fraction"] is not None]

        snow_med = round(median(snows), 3) if snows else 0.0
        temp_med_f = round(median(temps_f), 1) if temps_f else None
        wind_med = round(median(winds), 1) if winds else None

        hourly_med_snow.append(snow_med)
        hourly_med_temp_c.append(((temp_med_f - 32.0) * 5.0 / 9.0) if temp_med_f is not None else None)
        hourly_med_wind_mph.append(wind_med)

        h_local = h_utc.astimezone(local_tz)
        timeline.append(
            {
                "time_utc": h_utc.isoformat(),
                "time_local": h_local.isoformat(),
                "local_date": h_local.date().isoformat(),
                "snow_min_in": round(min(snows), 3) if snows else 0.0,
                "snow_median_in": snow_med,
                "snow_max_in": round(max(snows), 3) if snows else 0.0,
                "settled_snow_in": 0.0,
                "precip_median_in": round(median(precips), 3) if precips else 0.0,
                "temp_median_f": temp_med_f,
                "temp_min_f": round(min(temps_f), 1) if temps_f else None,
                "temp_max_f": round(max(temps_f), 1) if temps_f else None,
                "wind_median_mph": wind_med,
                "wind_gust_max_mph": round(max(gusts), 1) if gusts else None,
                "snow_level_median_ft": round(median(snow_lvls)) if snow_lvls else None,
                "slr_median": round(median(slrs), 1) if slrs else None,
                "snow_fraction_median": round(median(fracs), 2) if fracs else None,
                "model_count": len(active),
            }
        )

    settled = apply_snowpack_settling(hourly_med_snow, hourly_med_temp_c, hourly_med_wind_mph)
    for row, settled_val in zip(timeline, settled):
        row["settled_snow_in"] = settled_val

    return timeline


def process_band_snapshot(
    band_key: str,
    band_data: dict[str, Any],
    anchor_utc: datetime,
    local_tz: ZoneInfo,
    elevation_m: float | None = None,
    horizon_hours: int = HORIZON_HOURS,
) -> dict[str, Any]:
    """Process all available forecast sources for a single resort elevation band."""
    band_elev_m = (
        elevation_m
        or band_data.get("elevation_m")
        or (float(band_data["elevation_ft"]) * 0.3048 if band_data.get("elevation_ft") is not None else None)
    )

    model_series: dict[str, list[dict[str, Any]]] = {}

    om = band_data.get("open_meteo") or {}
    if om.get("status") == "ok":
        for model_name, model_payload in (om.get("models") or {}).items():
            hourly_rows = model_payload.get("hourly") or []
            if hourly_rows:
                model_series[model_name] = _normalize_open_meteo_model(
                    hourly_rows, anchor_utc, horizon_hours, band_elev_m
                )

    met = band_data.get("met_no") or {}
    if met.get("status") == "ok" and (met.get("intervals") or []):
        model_series["met_no"] = _normalize_met_no(met, anchor_utc, horizon_hours, band_elev_m)

    nws = band_data.get("nws") or {}
    if nws.get("status") == "ok" and (nws.get("layers") or {}):
        model_series["nws_gridpoints"] = _normalize_nws(nws, anchor_utc, horizon_hours, band_elev_m)

    # Window summaries across models & consensus
    windows: dict[str, Any] = {}
    for win_h in STANDARD_WINDOWS_HOURS:
        indices = list(range(min(win_h, horizon_hours)))
        windows[f"{win_h}h"] = _aggregate_consensus_slice(indices, model_series, min_coverage_ratio=0.88)

    # Individual model breakdown (windows + coverage)
    models_out: dict[str, Any] = {}
    for model_id, rows in model_series.items():
        covered_hours = sum(1 for r in rows if r["covered"])
        if covered_hours == 0:
            continue
        model_windows = {
            f"{win_h}h": _summarize_model_slice(rows[:win_h])
            for win_h in STANDARD_WINDOWS_HOURS
        }
        models_out[model_id] = {
            "id": model_id,
            "display_name": MODEL_DISPLAY_NAMES.get(model_id, model_id),
            "coverage_hours": covered_hours,
            "windows": model_windows,
        }

    # Consensus hourly timeline
    hourly_consensus = _build_consensus_hourly(model_series, anchor_utc, horizon_hours, local_tz)

    # Local-timezone daily buckets
    by_local_date: dict[str, list[int]] = {}
    for idx, h_row in enumerate(hourly_consensus):
        by_local_date.setdefault(h_row["local_date"], []).append(idx)

    daily: list[dict[str, Any]] = []
    for day_iso in sorted(by_local_date.keys()):
        day_indices = by_local_date[day_iso]
        day_slice = _aggregate_consensus_slice(day_indices, model_series, min_coverage_ratio=0.75)
        dt_obj = datetime.fromisoformat(day_iso)
        day_slice.update(
            {
                "date": day_iso,
                "day_name": f"{dt_obj.strftime('%a %b')} {dt_obj.day}",
                "hours_in_bucket": len(day_indices),
                "is_partial": len(day_indices) < 20,
            }
        )
        daily.append(day_slice)

    return {
        "label": band_data.get("label", band_key.title()),
        "elevation_ft": band_data.get("elevation_ft"),
        "elevation_m": round(band_elev_m, 1) if band_elev_m is not None else None,
        "windows": windows,
        "daily": daily,
        "hourly": hourly_consensus,
        "models": models_out,
    }


def build_resort_summary(processed_resort: dict[str, Any], fetched_at_utc: str) -> dict[str, Any]:
    """Build lightweight summary for GET /api/resorts."""
    bands_summary: dict[str, Any] = {}
    for band_key, band_val in processed_resort["bands"].items():
        bands_summary[band_key] = {
            "label": band_val["label"],
            "elevation_ft": band_val["elevation_ft"],
            "windows": band_val["windows"],
        }

    return {
        "id": processed_resort["id"],
        "name": processed_resort["name"],
        "region": processed_resort["region"],
        "state": processed_resort["state"],
        "timezone": processed_resort["timezone"],
        "fetched_at_utc": fetched_at_utc,
        "current_snowpack": processed_resort.get("current_snowpack"),
        "bands": bands_summary,
    }


def process_resort_snapshot(
    resort_snapshot: dict[str, Any],
    anchor_utc: datetime,
    resort_meta: dict[str, Any] | None = None,
    horizon_hours: int = HORIZON_HOURS,
) -> dict[str, Any]:
    """Process all elevation bands for one resort."""
    tz_name = resort_snapshot.get("timezone") or (resort_meta or {}).get("timezone") or "UTC"
    local_tz = ZoneInfo(tz_name)

    processed_bands: dict[str, Any] = {}
    meta_bands = (resort_meta or {}).get("bands") or {}
    for band_key, band_data in (resort_snapshot.get("bands") or {}).items():
        elev_m = band_data.get("elevation_m") or (meta_bands.get(band_key) or {}).get("reported_elevation_m")
        processed_bands[band_key] = process_band_snapshot(
            band_key=band_key,
            band_data=band_data,
            anchor_utc=anchor_utc,
            local_tz=local_tz,
            elevation_m=elev_m,
            horizon_hours=horizon_hours,
        )

    return {
        "id": resort_snapshot["id"],
        "name": resort_snapshot["name"],
        "region": resort_snapshot["region"],
        "state": resort_snapshot["state"],
        "timezone": tz_name,
        "current_snowpack": resort_snapshot.get("current_snowpack"),
        "bands": processed_bands,
    }


def process_snapshot(
    snapshot: dict[str, Any],
    resorts_meta: list[dict[str, Any]] | None = None,
    reference_time: datetime | None = None,
    horizon_hours: int = HORIZON_HOURS,
) -> dict[str, Any]:
    """Transform a Step 2 raw snapshot into Step 3 consensus forecasts."""
    fetched_at_str = snapshot.get("fetched_at_utc") or datetime.now(timezone.utc).isoformat()
    anchor_raw = reference_time or parse_utc(fetched_at_str)
    anchor_utc = floor_utc_hour(anchor_raw)

    meta_by_id = {r["id"]: r for r in (resorts_meta or [])}

    processed_resorts: list[dict[str, Any]] = []
    summaries: list[dict[str, Any]] = []
    for r_snap in snapshot.get("resorts") or []:
        processed = process_resort_snapshot(
            resort_snapshot=r_snap,
            anchor_utc=anchor_utc,
            resort_meta=meta_by_id.get(r_snap["id"]),
            horizon_hours=horizon_hours,
        )
        processed["fetched_at_utc"] = fetched_at_str
        processed["anchor_utc"] = anchor_utc.isoformat()
        processed_resorts.append(processed)
        summaries.append(build_resort_summary(processed, fetched_at_str))

    return {
        "fetched_at_utc": fetched_at_str,
        "anchor_utc": anchor_utc.isoformat(),
        "models_requested": snapshot.get("models_requested") or [],
        "resorts": processed_resorts,
        "summaries": summaries,
    }
