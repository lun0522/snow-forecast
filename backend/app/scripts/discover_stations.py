"""Step 1: Enrich seed resorts with DEM elevations, NWS gridpoints, and nearest SNOTEL stations."""

from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.fetchers.nws import discover_gridpoint
from app.fetchers.open_meteo import fetch_dem_elevations
from app.fetchers.snotel import fetch_snotel_stations, find_nearest_snotel_stations
from app.geo import meters_to_feet
from app.http_client import HttpFetchError
from app.resorts_seed import SEED_RESORTS

DEFAULT_OUTPUT_PATH = Path(__file__).resolve().parent.parent / "resorts.json"


def discover_all_resorts(output_path: Path = DEFAULT_OUTPUT_PATH) -> dict[str, Any]:
    """Query public metadata APIs and save verified resort + station config JSON."""
    resorts = deepcopy(SEED_RESORTS)

    # 1. Best-effort Copernicus 90m DEM lookup from Open-Meteo
    coords: list[tuple[float, float]] = []
    coord_refs: list[tuple[int, str]] = []
    for idx, resort in enumerate(resorts):
        for band_key, band in resort["bands"].items():
            coords.append((band["lat"], band["lon"]))
            coord_refs.append((idx, band_key))

    try:
        dem_elevations = fetch_dem_elevations(coords, timeout=6.0, retries=1)
        for (idx, band_key), dem_m in zip(coord_refs, dem_elevations):
            band = resorts[idx]["bands"][band_key]
            band["dem_elevation_m"] = round(dem_m, 1) if dem_m is not None else None
            band["dem_elevation_ft"] = round(meters_to_feet(dem_m)) if dem_m is not None else None
    except HttpFetchError as exc:
        print(f"[warn] Open-Meteo DEM lookup unavailable ({exc}); keeping reported elevations.")

    # 2. Fetch all active SNOTEL stations across target states once
    all_snotel = fetch_snotel_stations(("CA", "NV", "UT", "CO"))

    # 3. Enrich each resort with nearest SNOTEL stations and NWS gridpoint endpoints
    for resort in resorts:
        mid = resort["bands"]["mid"]
        resort["snotel_stations"] = find_nearest_snotel_stations(
            mid["lat"],
            mid["lon"],
            all_snotel,
            limit=3,
            max_distance_km=50.0,
        )

        for band_key in ("base", "summit"):
            band = resort["bands"][band_key]
            band["nws"] = discover_gridpoint(band["lat"], band["lon"])

    doc = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "snotel_catalog_count": len(all_snotel),
        "resorts": resorts,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    return doc


def _print_summary(doc: dict[str, Any], output_path: Path) -> None:
    print(f"Discovered {doc['snotel_catalog_count']} active SNOTEL stations across CA/NV/UT/CO.")
    print(f"Saved resort registry to {output_path}\n")
    for resort in doc["resorts"]:
        print(f"=== {resort['name']} ({resort['region']}, {resort['state']}) ===")
        for band_key in ("base", "mid", "summit"):
            b = resort["bands"][band_key]
            dem_str = f" (DEM: {b['dem_elevation_ft']} ft)" if b.get("dem_elevation_ft") else ""
            nws_str = ""
            if "nws" in b and b["nws"].get("grid_id"):
                nws = b["nws"]
                nws_str = f" | NWS {nws['grid_id']}:{nws['grid_x']},{nws['grid_y']}"
            print(
                f"  {band_key:<6} {b['reported_elevation_ft']:>5} ft{dem_str} "
                f"@ ({b['lat']:.4f}, {b['lon']:.4f}){nws_str}"
            )
        print("  Nearest SNOTEL:")
        for st in resort["snotel_stations"]:
            print(
                f"    - {st['triplet']:<13} {st['name']:<24} "
                f"{st['elevation_ft']:>5.0f} ft  ({st['distance_mi']:>4.1f} mi / {st['distance_km']:>4.1f} km)"
            )
        print()


def main() -> None:
    doc = discover_all_resorts()
    _print_summary(doc, DEFAULT_OUTPUT_PATH)


if __name__ == "__main__":
    main()
