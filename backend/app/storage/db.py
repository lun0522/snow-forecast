"""SQLite database schema, run persistence, and historical query helpers."""

from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_DB_PATH = Path(
    os.environ.get(
        "SNOW_DB_PATH",
        str(Path(__file__).resolve().parents[2] / "data" / "snow.db"),
    )
)

SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS forecast_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fetched_at_utc TEXT NOT NULL UNIQUE,
    created_at_utc TEXT NOT NULL,
    status TEXT NOT NULL,
    models_json TEXT NOT NULL,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS band_window_forecasts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL REFERENCES forecast_runs(id) ON DELETE CASCADE,
    resort_id TEXT NOT NULL,
    band_key TEXT NOT NULL,
    window_key TEXT NOT NULL,
    snow_min_in REAL,
    snow_median_in REAL,
    snow_max_in REAL,
    native_snow_median_in REAL,
    precip_median_in REAL,
    avg_slr REAL,
    temp_min_f REAL,
    temp_max_f REAL,
    max_wind_mph REAL,
    snow_level_min_ft INTEGER,
    snow_level_max_ft INTEGER,
    rain_snow_risk TEXT,
    confidence TEXT,
    model_count INTEGER,
    UNIQUE(run_id, resort_id, band_key, window_key)
);

CREATE TABLE IF NOT EXISTS resort_run_payloads (
    run_id INTEGER NOT NULL REFERENCES forecast_runs(id) ON DELETE CASCADE,
    resort_id TEXT NOT NULL,
    summary_json TEXT NOT NULL,
    detail_json TEXT NOT NULL,
    PRIMARY KEY (run_id, resort_id)
);

CREATE INDEX IF NOT EXISTS idx_bwf_lookup
    ON band_window_forecasts (resort_id, band_key, window_key, run_id);
"""


def get_connection(db_path: Path = DEFAULT_DB_PATH) -> sqlite3.Connection:
    """Open a SQLite connection configured with Row factory and foreign-key enforcement."""
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path), timeout=15.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path: Path = DEFAULT_DB_PATH) -> None:
    """Create database tables and indexes idempotently."""
    with get_connection(db_path) as conn:
        conn.executescript(SCHEMA_SQL)


def save_forecast_run(
    processed: dict[str, Any],
    db_path: Path = DEFAULT_DB_PATH,
    status: str = "ok",
    notes: str | None = None,
) -> int:
    """Persist a Step 3 processed run, band windows, and resort payloads."""
    init_db(db_path)
    fetched_at = processed["fetched_at_utc"]
    created_at = datetime.now(timezone.utc).isoformat()
    models_json = json.dumps(processed.get("models_requested") or [])

    summaries_by_id = {s["id"]: s for s in (processed.get("summaries") or [])}

    with get_connection(db_path) as conn:
        existing = conn.execute(
            "SELECT id FROM forecast_runs WHERE fetched_at_utc = ?",
            (fetched_at,),
        ).fetchone()
        if existing is not None:
            conn.execute("DELETE FROM forecast_runs WHERE id = ?", (existing["id"],))

        cursor = conn.execute(
            """
            INSERT INTO forecast_runs (fetched_at_utc, created_at_utc, status, models_json, notes)
            VALUES (?, ?, ?, ?, ?)
            """,
            (fetched_at, created_at, status, models_json, notes),
        )
        run_id = int(cursor.lastrowid)

        bwf_rows: list[tuple[Any, ...]] = []
        payload_rows: list[tuple[Any, ...]] = []

        for resort in processed.get("resorts") or []:
            resort_id = resort["id"]
            summary = summaries_by_id.get(resort_id) or {}
            payload_rows.append(
                (
                    run_id,
                    resort_id,
                    json.dumps(summary),
                    json.dumps(resort),
                )
            )

            for band_key, band_val in (resort.get("bands") or {}).items():
                for win_key, win_val in (band_val.get("windows") or {}).items():
                    bwf_rows.append(
                        (
                            run_id,
                            resort_id,
                            band_key,
                            win_key,
                            win_val.get("snow_min_in"),
                            win_val.get("snow_median_in"),
                            win_val.get("snow_max_in"),
                            win_val.get("native_snow_median_in"),
                            win_val.get("precip_median_in"),
                            win_val.get("avg_slr"),
                            win_val.get("temp_min_f"),
                            win_val.get("temp_max_f"),
                            win_val.get("max_wind_mph"),
                            win_val.get("snow_level_min_ft"),
                            win_val.get("snow_level_max_ft"),
                            win_val.get("rain_snow_risk"),
                            win_val.get("confidence"),
                            win_val.get("model_count"),
                        )
                    )

        conn.executemany(
            """
            INSERT INTO band_window_forecasts (
                run_id, resort_id, band_key, window_key,
                snow_min_in, snow_median_in, snow_max_in, native_snow_median_in,
                precip_median_in, avg_slr, temp_min_f, temp_max_f, max_wind_mph,
                snow_level_min_ft, snow_level_max_ft, rain_snow_risk, confidence, model_count
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            bwf_rows,
        )
        conn.executemany(
            """
            INSERT INTO resort_run_payloads (run_id, resort_id, summary_json, detail_json)
            VALUES (?, ?, ?, ?)
            """,
            payload_rows,
        )

    return run_id


def _row_to_run(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "fetched_at_utc": row["fetched_at_utc"],
        "created_at_utc": row["created_at_utc"],
        "status": row["status"],
        "models_requested": json.loads(row["models_json"]),
        "notes": row["notes"],
    }


def list_runs(limit: int = 20, db_path: Path = DEFAULT_DB_PATH) -> list[dict[str, Any]]:
    """Return recent forecast runs ordered newest first."""
    init_db(db_path)
    with get_connection(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM forecast_runs ORDER BY fetched_at_utc DESC, id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [_row_to_run(r) for r in rows]


def get_latest_run(db_path: Path = DEFAULT_DB_PATH) -> dict[str, Any] | None:
    """Return metadata for the newest forecast run, or None if DB is empty."""
    runs = list_runs(limit=1, db_path=db_path)
    return runs[0] if runs else None


def _get_run_row(conn: sqlite3.Connection, run_id: int | None) -> sqlite3.Row | None:
    if run_id is not None:
        return conn.execute("SELECT * FROM forecast_runs WHERE id = ?", (run_id,)).fetchone()
    return conn.execute(
        "SELECT * FROM forecast_runs ORDER BY fetched_at_utc DESC, id DESC LIMIT 1"
    ).fetchone()


def get_resort_summaries(
    run_id: int | None = None,
    db_path: Path = DEFAULT_DB_PATH,
) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    """Load overview summaries for all resorts in the target/latest run with run-to-run deltas."""
    init_db(db_path)
    with get_connection(db_path) as conn:
        run_row = _get_run_row(conn, run_id)
        if run_row is None:
            return None, []

        run_meta = _row_to_run(run_row)
        payload_rows = conn.execute(
            "SELECT resort_id, summary_json FROM resort_run_payloads WHERE run_id = ?",
            (run_row["id"],),
        ).fetchall()

        prev_row = conn.execute(
            """
            SELECT id, fetched_at_utc FROM forecast_runs
            WHERE fetched_at_utc < ?
            ORDER BY fetched_at_utc DESC, id DESC LIMIT 1
            """,
            (run_row["fetched_at_utc"],),
        ).fetchone()

        prev_deltas: dict[tuple[str, str], float] = {}
        if prev_row is not None:
            prev_bwf = conn.execute(
                """
                SELECT resort_id, window_key, snow_median_in
                FROM band_window_forecasts
                WHERE run_id = ? AND band_key = 'summit' AND window_key IN ('72h', '168h')
                """,
                (prev_row["id"],),
            ).fetchall()
            for r in prev_bwf:
                if r["snow_median_in"] is not None:
                    prev_deltas[(r["resort_id"], r["window_key"])] = float(r["snow_median_in"])

        summaries: list[dict[str, Any]] = []
        for p_row in payload_rows:
            summary = json.loads(p_row["summary_json"])
            rid = summary.get("id")
            summit_wins = ((summary.get("bands") or {}).get("summit") or {}).get("windows") or {}
            curr_72 = (summit_wins.get("72h") or {}).get("snow_median_in")
            curr_168 = (summit_wins.get("168h") or {}).get("snow_median_in")

            summary["run_id"] = run_meta["id"]
            if prev_row is not None and rid:
                p72 = prev_deltas.get((rid, "72h"))
                p168 = prev_deltas.get((rid, "168h"))
                summary["run_delta"] = {
                    "previous_run_at_utc": prev_row["fetched_at_utc"],
                    "summit_72h_in": round(curr_72 - p72, 2) if curr_72 is not None and p72 is not None else None,
                    "summit_168h_in": round(curr_168 - p168, 2) if curr_168 is not None and p168 is not None else None,
                }
            else:
                summary["run_delta"] = None

            summaries.append(summary)

    return run_meta, summaries


def get_resort_detail(
    resort_id: str,
    run_id: int | None = None,
    db_path: Path = DEFAULT_DB_PATH,
) -> dict[str, Any] | None:
    """Return full processed forecast payload for a resort in the target/latest run."""
    init_db(db_path)
    with get_connection(db_path) as conn:
        run_row = _get_run_row(conn, run_id)
        if run_row is None:
            return None
        row = conn.execute(
            "SELECT detail_json FROM resort_run_payloads WHERE run_id = ? AND resort_id = ?",
            (run_row["id"], resort_id),
        ).fetchone()
        if row is None:
            return None
        payload = json.loads(row["detail_json"])
        payload["run_id"] = run_row["id"]
        return payload
