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
DEFAULT_KEEP_RUNS = 10

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

CREATE TABLE IF NOT EXISTS resort_run_payloads (
    run_id INTEGER NOT NULL REFERENCES forecast_runs(id) ON DELETE CASCADE,
    resort_id TEXT NOT NULL,
    summary_json TEXT NOT NULL,
    detail_json TEXT NOT NULL,
    PRIMARY KEY (run_id, resort_id)
);
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
    """Create database tables idempotently and drop legacy unused tables."""
    with get_connection(db_path) as conn:
        conn.executescript(SCHEMA_SQL)
        conn.execute("DROP TABLE IF EXISTS band_window_forecasts")
        conn.execute("DROP TABLE IF EXISTS station_observations")


def vacuum_db(db_path: Path = DEFAULT_DB_PATH) -> None:
    """Reclaim free SQLite pages after pruning old forecast runs."""
    conn = sqlite3.connect(str(Path(db_path)), timeout=15.0, isolation_level=None)
    try:
        conn.execute("VACUUM")
    finally:
        conn.close()


def _prune_runs_in_conn(conn: sqlite3.Connection, keep_runs: int) -> int:
    cursor = conn.execute(
        """
        DELETE FROM forecast_runs
        WHERE id NOT IN (
            SELECT id FROM forecast_runs
            ORDER BY fetched_at_utc DESC, id DESC
            LIMIT ?
        )
        """,
        (keep_runs,),
    )
    return int(cursor.rowcount or 0)


def prune_old_runs(
    keep_runs: int = DEFAULT_KEEP_RUNS,
    vacuum: bool = True,
    db_path: Path = DEFAULT_DB_PATH,
) -> int:
    """Delete forecast runs beyond the newest ``keep_runs`` entries and optionally VACUUM."""
    if keep_runs < 1:
        raise ValueError("keep_runs must be >= 1")
    init_db(db_path)
    with get_connection(db_path) as conn:
        deleted = _prune_runs_in_conn(conn, keep_runs)
    if deleted > 0 and vacuum:
        vacuum_db(db_path)
    return deleted


def save_forecast_run(
    processed: dict[str, Any],
    db_path: Path = DEFAULT_DB_PATH,
    status: str = "ok",
    notes: str | None = None,
    keep_runs: int | None = DEFAULT_KEEP_RUNS,
) -> int:
    """Persist a Step 3 processed run and resort payloads, pruning older runs beyond ``keep_runs``."""
    init_db(db_path)
    fetched_at = processed["fetched_at_utc"]
    created_at = datetime.now(timezone.utc).isoformat()
    models_json = json.dumps(processed.get("models_requested") or [])

    summaries_by_id = {s["id"]: s for s in (processed.get("summaries") or [])}
    deleted = 0

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

        payload_rows = [
            (
                run_id,
                resort["id"],
                json.dumps(summaries_by_id.get(resort["id"]) or {}),
                json.dumps(resort),
            )
            for resort in (processed.get("resorts") or [])
        ]
        conn.executemany(
            """
            INSERT INTO resort_run_payloads (run_id, resort_id, summary_json, detail_json)
            VALUES (?, ?, ?, ?)
            """,
            payload_rows,
        )

        if keep_runs is not None and keep_runs > 0:
            deleted = _prune_runs_in_conn(conn, keep_runs)

    if deleted > 0:
        vacuum_db(db_path)

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
    """Load overview summaries for all resorts in the target/latest run."""
    init_db(db_path)
    with get_connection(db_path) as conn:
        run_row = _get_run_row(conn, run_id)
        if run_row is None:
            return None, []

        run_meta = _row_to_run(run_row)
        payload_rows = conn.execute(
            "SELECT summary_json FROM resort_run_payloads WHERE run_id = ?",
            (run_row["id"],),
        ).fetchall()

        summaries: list[dict[str, Any]] = []
        for p_row in payload_rows:
            summary = json.loads(p_row["summary_json"])
            summary["run_id"] = run_meta["id"]
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
