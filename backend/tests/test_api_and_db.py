"""Unit and integration tests for Step 4 SQLite persistence, update CLI, and FastAPI routes."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import tempfile
import unittest

from fastapi.testclient import TestClient

from app.main import create_app
from app.scripts.update import run_update_pipeline
from app.storage.db import get_resort_detail, get_resort_summaries


def _make_resorts_config() -> dict:
    return {
        "generated_at_utc": "2026-11-14T00:00:00+00:00",
        "resorts": [
            {
                "id": "kirkwood",
                "name": "Kirkwood Mountain",
                "region": "Lake Tahoe",
                "state": "CA",
                "timezone": "America/Los_Angeles",
                "bands": {
                    "base": {"label": "Base", "lat": 38.68, "lon": -120.06, "reported_elevation_ft": 7800, "reported_elevation_m": 2377.4},
                    "mid": {"label": "Mid", "lat": 38.68, "lon": -120.06, "reported_elevation_ft": 8800, "reported_elevation_m": 2682.2},
                    "summit": {"label": "Summit", "lat": 38.67, "lon": -120.06, "reported_elevation_ft": 9800, "reported_elevation_m": 2987.0},
                },
            }
        ],
    }


def _make_snapshot(fetched_at: datetime, precip_mm_per_hour: float) -> dict:
    anchor = fetched_at.replace(minute=0, second=0, microsecond=0)
    ecmwf_rows = [
        {
            "time_utc": (anchor + timedelta(hours=h)).isoformat(),
            "temp_c": -6.0,
            "temp_f": 21.2,
            "rh_pct": 90.0,
            "precip_mm": precip_mm_per_hour if h < 12 else 0.0,
            "snowfall_cm": (precip_mm_per_hour * 1.4 / 10.0) if h < 12 else 0.0,
            "snowfall_in": (precip_mm_per_hour * 1.4 / 25.4) if h < 12 else 0.0,
            "freezing_level_m": 1800.0,
            "wind_mph": 12.0,
            "wind_gust_mph": 20.0,
            "wind_dir_deg": 250.0,
        }
        for h in range(168)
    ]
    gfs_rows = [
        {
            **row,
            "precip_mm": (precip_mm_per_hour * 1.2) if idx < 12 else 0.0,
        }
        for idx, row in enumerate(ecmwf_rows)
    ]

    return {
        "fetched_at_utc": fetched_at.isoformat(),
        "models_requested": ["ecmwf_ifs025", "gfs_global"],
        "resorts": [
            {
                "id": "kirkwood",
                "name": "Kirkwood Mountain",
                "region": "Lake Tahoe",
                "state": "CA",
                "timezone": "America/Los_Angeles",
                "bands": {
                    key: {
                        "label": label,
                        "elevation_ft": elev,
                        "open_meteo": {
                            "status": "ok",
                            "models": {
                                "ecmwf_ifs025": {"hourly": ecmwf_rows},
                                "gfs_global": {"hourly": gfs_rows},
                            },
                        },
                        "met_no": {"status": "unavailable"},
                        "nws": None,
                    }
                    for key, label, elev in (("base", "Base", 7800), ("mid", "Mid", 8800), ("summit", "Summit", 9800))
                },
            }
        ],
    }


class ApiAndDbTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self._tmp.name)
        self.db_path = self.tmp_path / "snow.db"
        self.resorts_path = self.tmp_path / "resorts.json"
        self.snapshot_path = self.tmp_path / "latest_snapshot.json"
        self.resorts_path.write_text(json.dumps(_make_resorts_config()), encoding="utf-8")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_update_pipeline_db_history_and_run_deltas(self) -> None:
        now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
        run1_snap = _make_snapshot(now - timedelta(hours=6), precip_mm_per_hour=1.0)
        run2_snap = _make_snapshot(now, precip_mm_per_hour=2.5)

        calls = {"n": 0}

        def fake_fetcher(_resorts):
            calls["n"] += 1
            return run1_snap if calls["n"] == 1 else run2_snap

        r1 = run_update_pipeline(
            db_path=self.db_path,
            resorts_path=self.resorts_path,
            snapshot_path=self.snapshot_path,
            fetcher=fake_fetcher,
        )
        r2 = run_update_pipeline(
            db_path=self.db_path,
            resorts_path=self.resorts_path,
            snapshot_path=self.snapshot_path,
            fetcher=fake_fetcher,
        )
        self.assertGreater(r2["run_id"], r1["run_id"])
        self.assertTrue(self.snapshot_path.exists())

        latest_meta, summaries = get_resort_summaries(db_path=self.db_path)
        self.assertIsNotNone(latest_meta)
        self.assertEqual(len(summaries), 1)
        self.assertIsNotNone(summaries[0]["run_delta"])
        self.assertGreater(summaries[0]["run_delta"]["summit_72h_in"], 0.0)

        detail = get_resort_detail("kirkwood", db_path=self.db_path)
        self.assertIsNotNone(detail)
        assert detail is not None
        self.assertEqual(len(detail["bands"]["summit"]["hourly"]), 168)

    def test_fastapi_endpoints_and_refresh_flow(self) -> None:
        now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
        snap = _make_snapshot(now, precip_mm_per_hour=2.0)

        app = create_app(
            db_path=self.db_path,
            resorts_path=self.resorts_path,
            snapshot_path=self.snapshot_path,
            fetcher=lambda _resorts: snap,
        )

        with TestClient(app) as client:
            health = client.get("/api/health")
            self.assertEqual(health.status_code, 200)
            self.assertIsNone(health.json()["latest_run"])

            empty_list = client.get("/api/resorts")
            self.assertEqual(empty_list.status_code, 200)
            self.assertEqual(empty_list.json()["resorts"], [])

            refresh = client.post("/api/refresh")
            self.assertEqual(refresh.status_code, 200)
            self.assertEqual(refresh.json()["resorts_count"], 1)

            resorts_resp = client.get("/api/resorts")
            self.assertEqual(resorts_resp.status_code, 200)
            data = resorts_resp.json()
            self.assertEqual(data["resorts"][0]["id"], "kirkwood")
            self.assertGreater(data["resorts"][0]["bands"]["summit"]["windows"]["24h"]["snow_median_in"], 0.0)

            detail_resp = client.get("/api/resorts/kirkwood")
            self.assertEqual(detail_resp.status_code, 200)
            self.assertIn("ecmwf_ifs025", detail_resp.json()["bands"]["summit"]["models"])

            bad_resort = client.get("/api/resorts/unknown")
            self.assertEqual(bad_resort.status_code, 404)


if __name__ == "__main__":
    unittest.main()
