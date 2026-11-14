"""Step 4 pipeline: fetch or load snapshot, run Step 3 snow engine, and persist to SQLite."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Callable

from app.engine.blending import process_snapshot
from app.scripts.fetch_snapshot import (
    DEFAULT_RESORTS_PATH,
    DEFAULT_SNAPSHOT_PATH,
    fetch_all_data,
    load_resorts,
)
from app.storage.db import DEFAULT_DB_PATH, save_forecast_run


def run_update_pipeline(
    db_path: Path = DEFAULT_DB_PATH,
    resorts_path: Path = DEFAULT_RESORTS_PATH,
    snapshot_path: Path | None = DEFAULT_SNAPSHOT_PATH,
    from_snapshot: bool = False,
    fetcher: Callable[[list[dict[str, Any]]], dict[str, Any]] = fetch_all_data,
) -> dict[str, Any]:
    """Execute ingestion (live or snapshot), physics/consensus processing, and SQLite save."""
    resorts_meta = load_resorts(resorts_path)

    if from_snapshot:
        if snapshot_path is None or not Path(snapshot_path).exists():
            raise FileNotFoundError(
                f"Snapshot not found at {snapshot_path}. Run fetch_snapshot or omit --from-snapshot."
            )
        snapshot = json.loads(Path(snapshot_path).read_text(encoding="utf-8"))
    else:
        snapshot = fetcher(resorts_meta)
        if snapshot_path is not None:
            out_path = Path(snapshot_path)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")

    processed = process_snapshot(snapshot, resorts_meta=resorts_meta)
    run_id = save_forecast_run(processed, db_path=db_path, status="ok")
    return {
        "run_id": run_id,
        "fetched_at_utc": processed["fetched_at_utc"],
        "anchor_utc": processed["anchor_utc"],
        "resorts_count": len(processed["resorts"]),
        "processed": processed,
    }


def _fmt_range(win: dict[str, Any]) -> str:
    lo = win.get("snow_min_in", 0.0)
    med = win.get("snow_median_in", 0.0)
    hi = win.get("snow_max_in", 0.0)
    return f'{med:4.1f}" ({lo:.1f}-{hi:.1f})'


def print_consensus_report(result: dict[str, Any]) -> None:
    """Print concise Step 3+4 consensus report for terminal inspection."""
    processed = result["processed"]
    print("=" * 100)
    print(
        f"RUN #{result['run_id']}  |  FETCHED: {result['fetched_at_utc']}  |  "
        f"ANCHOR: {result['anchor_utc']}"
    )
    print("=" * 100)
    for resort in processed["resorts"]:
        print(f"\n[{resort['name']}] ({resort['region']} | {resort['timezone']})")
        for band_key in ("base", "mid", "summit"):
            band = resort["bands"].get(band_key)
            if not band:
                continue
            w = band["windows"]
            sl_min = w["72h"].get("snow_level_min_ft")
            sl_max = w["72h"].get("snow_level_max_ft")
            sl_str = f"{sl_min:,}-{sl_max:,}ft" if sl_min is not None and sl_max is not None else "n/a"
            print(
                f"  {band['label']:<7} ({band['elevation_ft']:>5}ft): "
                f"24h={_fmt_range(w['24h'])}  "
                f"72h={_fmt_range(w['72h'])}  "
                f"7d={_fmt_range(w['168h'])}  "
                f"SLR={w['72h']['avg_slr']:4.1f}:1  "
                f"SnowLvl={sl_str:<13} "
                f"[{w['72h']['confidence'].upper()} | {w['72h']['model_count']}m]"
            )


def main() -> None:
    parser = argparse.ArgumentParser(description="Update ski snow forecasts into SQLite.")
    parser.add_argument(
        "--from-snapshot",
        action="store_true",
        help="Process an existing raw JSON snapshot into SQLite instead of fetching live APIs.",
    )
    parser.add_argument(
        "--snapshot",
        type=Path,
        default=DEFAULT_SNAPSHOT_PATH,
        help="Path to snapshot JSON (read when --from-snapshot, written on live fetch).",
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=DEFAULT_DB_PATH,
        help="Path to SQLite database.",
    )
    args = parser.parse_args()

    result = run_update_pipeline(
        db_path=args.db,
        snapshot_path=args.snapshot,
        from_snapshot=args.from_snapshot,
    )
    print_consensus_report(result)


if __name__ == "__main__":
    main()
