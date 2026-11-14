"""FastAPI REST API for the ski-resort snow forecast engine."""

from __future__ import annotations

import threading
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Callable

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from app.http_client import HttpFetchError
from app.scripts.fetch_snapshot import (
    DEFAULT_RESORTS_PATH,
    DEFAULT_SNAPSHOT_PATH,
    fetch_all_data,
    load_resorts,
)
from app.scripts.update import run_update_pipeline
from app.storage.db import (
    DEFAULT_DB_PATH,
    get_latest_run,
    get_resort_detail,
    get_resort_summaries,
    init_db,
    list_runs,
)


def create_app(
    db_path: Path | None = None,
    resorts_path: Path | None = None,
    snapshot_path: Path | None = None,
    fetcher: Callable[[list[dict[str, Any]]], dict[str, Any]] | None = None,
) -> FastAPI:
    """Construct the FastAPI application with configurable paths and fetcher for testing."""
    resolved_db = Path(db_path) if db_path is not None else DEFAULT_DB_PATH
    resolved_resorts = Path(resorts_path) if resorts_path is not None else DEFAULT_RESORTS_PATH
    resolved_snapshot = Path(snapshot_path) if snapshot_path is not None else DEFAULT_SNAPSHOT_PATH
    resolved_fetcher = fetcher or fetch_all_data
    refresh_lock = threading.Lock()

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        init_db(resolved_db)
        yield

    application = FastAPI(
        title="Snow Forecast API",
        version="0.4.0",
        description="Public-data mountain snow physics & multi-model consensus API.",
        lifespan=lifespan,
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    def _resort_order() -> dict[str, int]:
        try:
            resorts = load_resorts(resolved_resorts)
            return {r["id"]: idx for idx, r in enumerate(resorts)}
        except FileNotFoundError:
            return {}

    def _known_resort_ids() -> set[str]:
        return set(_resort_order().keys())

    @application.get("/api/health")
    def health_check() -> dict[str, Any]:
        latest = get_latest_run(db_path=resolved_db)
        resorts = _resort_order()
        return {
            "status": "ok",
            "latest_run": latest,
            "resorts_count": len(resorts),
            "db_path": str(resolved_db),
        }

    @application.get("/api/runs")
    def get_runs(limit: int = Query(default=20, ge=1, le=100)) -> dict[str, Any]:
        return {"runs": list_runs(limit=limit, db_path=resolved_db)}

    @application.get("/api/resorts")
    def get_resorts(run_id: int | None = Query(default=None, ge=1)) -> dict[str, Any]:
        run_meta, summaries = get_resort_summaries(run_id=run_id, db_path=resolved_db)
        if run_id is not None and run_meta is None:
            raise HTTPException(status_code=404, detail=f"Forecast run {run_id} not found")
        order = _resort_order()
        summaries.sort(key=lambda s: order.get(s["id"], 999))
        return {
            "run": run_meta,
            "resorts": summaries,
        }

    @application.get("/api/resorts/{resort_id}")
    def get_resort(resort_id: str, run_id: int | None = Query(default=None, ge=1)) -> dict[str, Any]:
        known = _known_resort_ids()
        if known and resort_id not in known:
            raise HTTPException(status_code=404, detail=f"Unknown resort '{resort_id}'")

        detail = get_resort_detail(resort_id=resort_id, run_id=run_id, db_path=resolved_db)
        if detail is None:
            raise HTTPException(
                status_code=404,
                detail=f"No forecast data found for resort '{resort_id}' (run POST /api/refresh first).",
            )
        return detail

    @application.post("/api/refresh")
    def refresh_forecasts() -> dict[str, Any]:
        if not refresh_lock.acquire(blocking=False):
            raise HTTPException(status_code=409, detail="Forecast refresh already in progress")

        try:
            result = run_update_pipeline(
                db_path=resolved_db,
                resorts_path=resolved_resorts,
                snapshot_path=resolved_snapshot,
                from_snapshot=False,
                fetcher=resolved_fetcher,
            )
        except HttpFetchError as exc:
            raise HTTPException(status_code=502, detail=f"Upstream data fetch failed: {exc}") from exc
        except FileNotFoundError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        finally:
            refresh_lock.release()

        order = _resort_order()
        summaries = list(result["processed"]["summaries"])
        summaries.sort(key=lambda s: order.get(s["id"], 999))
        return {
            "status": "ok",
            "run_id": result["run_id"],
            "fetched_at_utc": result["fetched_at_utc"],
            "resorts_count": result["resorts_count"],
            "resorts": summaries,
        }

    return application


app = create_app()
