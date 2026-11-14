"""Mountain snow physics: wet-bulb partitioning, dynamic SLR, wind fracturing, and compaction."""

from __future__ import annotations

import math
from typing import Iterable


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _lerp(x: float, x0: float, y0: float, x1: float, y1: float) -> float:
    if x1 == x0:
        return y0
    t = _clamp((x - x0) / (x1 - x0), 0.0, 1.0)
    return y0 + t * (y1 - y0)


def compute_wet_bulb_c(temp_c: float | None, rh_pct: float | None) -> float | None:
    """Compute Stull (2011) wet-bulb temperature (C) from air temperature and relative humidity.

    Falls back to dry-bulb ``temp_c`` when relative humidity is missing.
    """
    if temp_c is None:
        return None
    if rh_pct is None:
        return float(temp_c)

    t = float(temp_c)
    rh = _clamp(float(rh_pct), 5.0, 100.0)

    return (
        t * math.atan(0.151977 * math.sqrt(rh + 8.313659))
        + math.atan(t + rh)
        - math.atan(rh - 1.676331)
        + 0.00391838 * (rh ** 1.5) * math.atan(0.023101 * rh)
        - 4.686035
    )


def estimate_snow_level_m(
    freezing_level_m: float | None = None,
    snow_level_m: float | None = None,
) -> float | None:
    """Return effective snow level (m), preferring explicit snow level over 0C freezing level - 250m."""
    if snow_level_m is not None:
        return float(snow_level_m)
    if freezing_level_m is not None:
        return float(freezing_level_m) - 250.0
    return None


def compute_snow_fraction(
    wet_bulb_c: float | None,
    band_elevation_m: float | None = None,
    freezing_level_m: float | None = None,
    snow_level_m: float | None = None,
) -> float:
    """Estimate fraction of liquid precipitation falling as snow (0.0..1.0).

    Combines surface wet-bulb phase partitioning with altitude vs forecaster/model snow level.
    """
    thermal_frac: float | None = None
    if wet_bulb_c is not None:
        if wet_bulb_c <= -0.5:
            thermal_frac = 1.0
        elif wet_bulb_c >= 2.2:
            thermal_frac = 0.0
        else:
            thermal_frac = (2.2 - wet_bulb_c) / 2.7

    eff_snow_level_m = estimate_snow_level_m(freezing_level_m=freezing_level_m, snow_level_m=snow_level_m)
    elev_frac: float | None = None
    if band_elevation_m is not None and eff_snow_level_m is not None:
        # Transition layer spanning +/- 150 m around the snow level
        elev_frac = _clamp((float(band_elevation_m) - (eff_snow_level_m - 150.0)) / 300.0, 0.0, 1.0)

    if thermal_frac is not None and elev_frac is not None:
        if wet_bulb_c is not None and wet_bulb_c >= 2.5:
            return 0.0
        if float(band_elevation_m) <= eff_snow_level_m - 300.0:  # type: ignore[arg-type,operator]
            return 0.0
        # Weight NWS explicit snowLevel strongly alongside surface wet-bulb
        if snow_level_m is not None:
            return round(_clamp(0.55 * thermal_frac + 0.45 * elev_frac, 0.0, 1.0), 3)
        return round(_clamp(0.7 * thermal_frac + 0.3 * elev_frac, 0.0, 1.0), 3)

    if thermal_frac is not None:
        return round(_clamp(thermal_frac, 0.0, 1.0), 3)
    if elev_frac is not None:
        return round(_clamp(elev_frac, 0.0, 1.0), 3)
    return 0.5


def classify_snow_fraction(snow_fraction: float) -> str:
    """Map snow fraction [0..1] to phase risk label: snow, mixed, or rain."""
    if snow_fraction >= 0.85:
        return "snow"
    if snow_fraction <= 0.15:
        return "rain"
    return "mixed"


def compute_dynamic_slr(wet_bulb_c: float | None, wind_mph: float | None = None) -> float:
    """Compute Snow-to-Liquid Ratio (SLR) from wet-bulb temp and wind-fracturing compaction.

    Peaks in the cold dendritic growth zone (-18C to -12C) and reduces ratio under winds > 15 mph.
    """
    if wet_bulb_c is None:
        base_slr = 10.0
    else:
        tw = float(wet_bulb_c)
        if tw >= 1.5:
            base_slr = 5.0
        elif tw >= 0.5:
            base_slr = _lerp(tw, 0.5, 8.0, 1.5, 5.0)
        elif tw >= -2.0:
            base_slr = _lerp(tw, -2.0, 11.0, 0.5, 8.0)
        elif tw >= -6.0:
            base_slr = _lerp(tw, -6.0, 14.5, -2.0, 11.0)
        elif tw >= -12.0:
            base_slr = _lerp(tw, -12.0, 18.5, -6.0, 14.5)
        elif tw >= -18.0:
            base_slr = _lerp(tw, -18.0, 20.0, -12.0, 18.5)
        else:
            # Extremely cold temperatures (< -18C) shift to finer plates/columns that pack tighter
            base_slr = _lerp(tw, -24.0, 17.5, -18.0, 20.0)

    if wind_mph is not None and wind_mph > 15.0:
        wind_factor = max(0.60, 1.0 - 0.015 * (float(wind_mph) - 15.0))
        base_slr *= wind_factor

    return round(_clamp(base_slr, 4.0, 22.0), 2)


def compute_hourly_physics_snow(
    precip_mm: float | None,
    temp_c: float | None,
    rh_pct: float | None = None,
    wind_mph: float | None = None,
    band_elevation_m: float | None = None,
    freezing_level_m: float | None = None,
    snow_level_m: float | None = None,
) -> dict[str, float | None]:
    """Compute hourly wet-bulb temp, snow fraction, dynamic SLR, and snow accumulation (inches)."""
    wet_bulb_c = compute_wet_bulb_c(temp_c, rh_pct)
    snow_frac = compute_snow_fraction(
        wet_bulb_c=wet_bulb_c,
        band_elevation_m=band_elevation_m,
        freezing_level_m=freezing_level_m,
        snow_level_m=snow_level_m,
    )
    slr = compute_dynamic_slr(wet_bulb_c=wet_bulb_c, wind_mph=wind_mph)
    precip_val = max(0.0, float(precip_mm)) if precip_mm is not None else 0.0
    snow_qpf_mm = precip_val * snow_frac
    # 1 mm liquid water = 1/25.4 inches; multiplied by SLR equals fresh snow depth in inches.
    physics_snow_in = (snow_qpf_mm / 25.4) * slr

    return {
        "wet_bulb_c": round(wet_bulb_c, 2) if wet_bulb_c is not None else None,
        "snow_fraction": snow_frac,
        "slr": slr,
        "snow_qpf_mm": round(snow_qpf_mm, 3),
        "physics_snow_in": round(physics_snow_in, 4),
    }


def apply_snowpack_settling(
    hourly_snow_in: Iterable[float],
    hourly_temp_c: Iterable[float | None] | None = None,
    hourly_wind_mph: Iterable[float | None] | None = None,
) -> list[float]:
    """Track settled storm snow depth (inches) over an hourly snowfall sequence.

    Applies gravitational settling, above-freezing warmth, and wind-packing decay each hour.
    """
    snow_list = list(hourly_snow_in)
    temp_list = list(hourly_temp_c) if hourly_temp_c is not None else [None] * len(snow_list)
    wind_list = list(hourly_wind_mph) if hourly_wind_mph is not None else [None] * len(snow_list)

    settled: list[float] = []
    depth = 0.0
    for idx, new_snow in enumerate(snow_list):
        t_c = temp_list[idx] if idx < len(temp_list) else None
        w_mph = wind_list[idx] if idx < len(wind_list) else None

        hourly_decay = 0.008  # Base gravitational settling (~17.5% over 24 hours)
        if t_c is not None and t_c > 0.0:
            hourly_decay += 0.006 * min(float(t_c), 5.0)
        if w_mph is not None and w_mph > 20.0:
            hourly_decay += 0.0005 * min(float(w_mph) - 20.0, 25.0)

        retain = _clamp(1.0 - hourly_decay, 0.94, 0.996)
        depth = max(0.0, depth * retain + max(0.0, float(new_snow)))
        settled.append(round(depth, 2))

    return settled
