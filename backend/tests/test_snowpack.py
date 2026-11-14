"""Unit tests for the unified natural snowpack telemetry adapters (SNOTEL & BC ASWS)."""

from __future__ import annotations

from datetime import datetime, timezone
import unittest
from unittest.mock import patch

from app.engine.blending import process_snapshot
from app.fetchers.bc_asws import parse_bc_asws_csv, parse_bc_stations_geojson
from app.fetchers.snowpack import (
    SNOWPACK_LABEL,
    fetch_current_snowpack_for_resorts,
    select_nearest_stations,
    summarize_latest_series,
)
from app.fetchers.snotel import parse_snotel_data_response, parse_snotel_stations
from app.http_client import HttpFetchError


def _sample_resorts() -> list[dict]:
    return [
        {
            "id": "kirkwood",
            "name": "Kirkwood Mountain",
            "region": "Sierra Crest",
            "state": "CA",
            "timezone": "America/Los_Angeles",
            "bands": {
                "mid": {
                    "label": "Mid-Mountain",
                    "lat": 38.6732,
                    "lon": -120.0643,
                    "reported_elevation_ft": 8800,
                    "reported_elevation_m": 2682.2,
                }
            },
        },
        {
            "id": "whistler-blackcomb",
            "name": "Whistler Blackcomb",
            "region": "Coast Mountains",
            "state": "BC",
            "timezone": "America/Vancouver",
            "bands": {
                "mid": {
                    "label": "Roundhouse Lodge",
                    "lat": 50.0696,
                    "lon": -122.9465,
                    "reported_elevation_ft": 6069,
                    "reported_elevation_m": 1849.8,
                }
            },
        },
    ]


class SnowpackCommonTests(unittest.TestCase):
    def test_select_nearest_stations_filters_and_sorts(self) -> None:
        stations = [
            {"id": "far", "name": "Too Far", "lat": 40.0, "lon": -120.0, "elevation_m": 2400},
            {"id": "near2", "name": "Second Closest", "lat": 38.68, "lon": -119.96, "elevation_m": 2450},
            {"id": "near1", "name": "Closest", "lat": 38.69, "lon": -120.00, "elevation_m": 2548},
        ]
        matched = select_nearest_stations(38.6732, -120.0643, stations, max_distance_km=50.0, limit=2)
        self.assertEqual([s["id"] for s in matched], ["near1", "near2"])
        self.assertLess(matched[0]["distance_km"], matched[1]["distance_km"])

    def test_summarize_latest_series_computes_24h_delta_and_clamps_noise(self) -> None:
        pts = [
            (datetime(2026, 11, 13, 8, 0, tzinfo=timezone.utc), 12.7),
            (datetime(2026, 11, 14, 8, 0, tzinfo=timezone.utc), 30.5),
            (datetime(2026, 11, 14, 9, 0, tzinfo=timezone.utc), -99.0),  # invalid sentinel skipped
        ]
        summary = summarize_latest_series(pts)
        self.assertIsNotNone(summary)
        assert summary is not None
        latest_cm, obs_utc, delta = summary
        self.assertEqual(latest_cm, 30.5)
        self.assertEqual(obs_utc, datetime(2026, 11, 14, 8, 0, tzinfo=timezone.utc))
        self.assertEqual(delta, 17.8)


class SnotelAdapterTests(unittest.TestCase):
    def test_parse_snotel_stations_and_hourly_data(self) -> None:
        raw_meta = [
            {
                "stationTriplet": "1067:CA:SNTL",
                "name": "Carson Pass",
                "latitude": 38.6927,
                "longitude": -120.0022,
                "elevation": 8360.0,
                "dataTimeZone": -8.0,
            }
        ]
        stations = parse_snotel_stations(raw_meta)
        self.assertEqual(len(stations), 1)
        self.assertAlmostEqual(stations[0]["elevation_m"], 2548.128, places=2)

        raw_data = [
            {
                "stationTriplet": "1067:CA:SNTL",
                "data": [
                    {
                        "stationElement": {"elementCode": "SNWD"},
                        "values": [
                            {"date": "2026-11-13 00:00", "value": 5},
                            {"date": "2026-11-14 00:00", "value": 12},
                        ],
                    },
                    {
                        "stationElement": {"elementCode": "WTEQ"},
                        "values": [
                            {"date": "2026-11-13 00:00", "value": 1.9},
                            {"date": "2026-11-14 00:00", "value": 2.7},
                        ],
                    },
                ],
            }
        ]
        parsed = parse_snotel_data_response(raw_data, tz_offsets={"1067:CA:SNTL": -8.0})
        rec = parsed["1067:CA:SNTL"]
        self.assertAlmostEqual(rec["snow_depth_cm"], 30.5)
        self.assertAlmostEqual(rec["delta_24h_cm"], 17.8)
        self.assertAlmostEqual(rec["swe_mm"], 68.6)
        self.assertEqual(rec["observed_utc"], datetime(2026, 11, 14, 8, 0, tzinfo=timezone.utc))


class BcAswsAdapterTests(unittest.TestCase):
    def test_parse_bc_stations_and_sparse_csv_tail(self) -> None:
        geojson = {
            "features": [
                {
                    "properties": {
                        "LOCATION_ID": "3A20P",
                        "LOCATION_NAME": "Callaghan Creek",
                        "LATITUDE": 50.1371,
                        "LONGITUDE": -123.1029,
                        "ELEVATION": 1017,
                        "STATUS": "Active",
                    }
                },
                {
                    "properties": {
                        "LOCATION_ID": "OLD01",
                        "LOCATION_NAME": "Retired",
                        "LATITUDE": 50.1,
                        "LONGITUDE": -123.0,
                        "ELEVATION": 1200,
                        "STATUS": "Inactive",
                    }
                },
            ]
        }
        stations = parse_bc_stations_geojson(geojson)
        self.assertEqual([s["id"] for s in stations], ["3A20P"])

        csv_text = "\n".join(
            [
                "DATE(UTC),1D06P Tenquille Lake,3A20P Callaghan Creek",
                "2026-11-13 06:00,18.0,1.0",
                "2026-11-14 05:00,22.0,2.0",
                "2026-11-14 07:00,24.0,",
            ]
        )
        parsed = parse_bc_asws_csv(csv_text, station_ids={"1D06P", "3A20P"})
        callaghan = summarize_latest_series(parsed["3A20P"])
        tenquille = summarize_latest_series(parsed["1D06P"])
        assert callaghan is not None and tenquille is not None
        self.assertEqual(callaghan[0], 2.0)
        self.assertEqual(tenquille[0], 24.0)
        self.assertEqual(tenquille[2], 6.0)


class DispatcherAndPreservationTests(unittest.TestCase):
    def test_dispatcher_routes_us_and_bc_and_handles_outage_gracefully(self) -> None:
        resorts = _sample_resorts()
        fake_us = {
            "kirkwood": {
                "status": "ok",
                "label": SNOWPACK_LABEL,
                "network": "snotel",
                "source_name": "USDA NRCS SNOTEL",
                "fetched_at_utc": "2026-11-14T08:00:00+00:00",
                "stations": [],
            }
        }
        with (
            patch("app.fetchers.snotel.fetch_snotel_snowpack_for_resorts", return_value=fake_us),
            patch(
                "app.fetchers.bc_asws.fetch_bc_asws_snowpack_for_resorts",
                side_effect=HttpFetchError("BC feed timeout"),
            ),
        ):
            out = fetch_current_snowpack_for_resorts(resorts)

        self.assertEqual(out["kirkwood"]["network"], "snotel")
        self.assertEqual(out["whistler-blackcomb"]["status"], "unavailable")
        self.assertEqual(out["whistler-blackcomb"]["label"], SNOWPACK_LABEL)

    def test_blending_preserves_current_snowpack(self) -> None:
        snowpack = {
            "status": "ok",
            "label": SNOWPACK_LABEL,
            "network": "snotel",
            "source_name": "USDA NRCS SNOTEL",
            "fetched_at_utc": "2026-11-14T08:00:00+00:00",
            "stations": [{"id": "1067:CA:SNTL", "name": "Carson Pass", "snow_depth_cm": 30.5}],
        }
        snap = {
            "fetched_at_utc": "2026-11-14T08:00:00+00:00",
            "models_requested": [],
            "resorts": [
                {
                    "id": "kirkwood",
                    "name": "Kirkwood Mountain",
                    "region": "Sierra Crest",
                    "state": "CA",
                    "timezone": "America/Los_Angeles",
                    "current_snowpack": snowpack,
                    "bands": {},
                }
            ],
        }
        processed = process_snapshot(snap)
        self.assertEqual(processed["resorts"][0]["current_snowpack"], snowpack)
        self.assertEqual(processed["summaries"][0]["current_snowpack"], snowpack)


if __name__ == "__main__":
    unittest.main()
