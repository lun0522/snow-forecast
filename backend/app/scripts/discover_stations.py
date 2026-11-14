"""Step 1: Enrich seed resorts with DEM elevations and NWS gridpoints."""

from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.fetchers.nws import discover_gridpoint
from app.fetchers.open_meteo import fetch_dem_elevations
from app.geo import meters_to_feet
from app.http_client import HttpFetchError
from app.resorts_seed import SEED_RESORTS

DEFAULT_OUTPUT_PATH = Path(__file__).resolve().parent.parent / "resorts.json"


def discover_all_resorts(output_path: Path = DEFAULT_OUTPUT_PATH) -> dict[str, Any]:
    """Query public metadata APIs and save verified resort config JSON."""
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

    # 2. Enrich each resort with NWS gridpoint endpoints
    for resort in resorts:
        for band_key in ("base", "summit"):
            band = resort["bands"][band_key]
            try:
                band["nws"] = discover_gridpoint(band["lat"], band["lon"])
            except HttpFetchError as exc:
                print(f"  WARN: NWS gridpoint lookup failed for {resort['id']} {band_key}: {exc}")
                band["nws"] = None

    doc = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "resorts": resorts,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    return doc


def _print_summary(doc: dict[str, Any], output_path: Path) -> None:
    print(f"Saved resort registry to {output_path}\n")
    for resort in doc["resorts"]:
        print(f"=== {resort['name']} ({resort['region']}, {resort['state']}) ===")
        for band_key in ("base", "mid", "summit"):
            b = resort["bands"][band_key]
            dem_str = f" (DEM: {b['dem_elevation_ft']} ft)" if b.get("dem_elevation_ft") else ""
            nws_str = ""
            if b.get("nws") and b["nws"].get("grid_id"):
                nws = b["nws"]
                nws_str = f" | NWS {nws['grid_id']}:{nws['grid_x']},{nws['grid_y']}"
            print(
                f"  {band_key:<6} {b['reported_elevation_ft']:>5} ft{dem_str} "
                f"@ ({b['lat']:.4f}, {b['lon']:.4f}){nws_str}"
            )
        print()


def main() -> None:
    doc = discover_all_resorts()
    _print_summary(doc, DEFAULT_OUTPUT_PATH)


if __name__ == "__main__":
    main()
