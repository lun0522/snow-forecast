"""Offline unit tests for geo helpers and Open-Meteo, NWS, and MET Norway parsers."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from app.fetchers.met_no import parse_met_no_response
from app.fetchers.nws import parse_grid_forecast_response, parse_iso_duration
from app.fetchers.open_meteo import parse_multi_model_response
from app.geo import haversine_km
from app.http_client import HttpFetchError
from app.scripts.fetch_snapshot import fetch_all_data


class GeoTests(unittest.TestCase):
    def test_haversine_known_distance(self) -> None:
        # Kirkwood base to Heavenly base is roughly 30 km
        dist = haversine_km(38.6840, -120.0680, 38.9353, -119.9400)
        self.assertGreater(dist, 28.0)
        self.assertLess(dist, 33.0)


class OpenMeteoParserTests(unittest.TestCase):
    def test_multi_model_series_extraction_preserves_missing_hours(self) -> None:
        times = [f"2026-11-14T{h:02d}:00" for h in range(24)] + [
            f"2026-11-15T{h:02d}:00" for h in range(24)
        ] + [f"2026-11-16T{h:02d}:00" for h in range(24)]
        # Model A covers all 72h; Model B (like HRRR) covers only first 24h
        payload = {
            "latitude": 39.25,
            "longitude": -120.13,
            "elevation": 2624.0,
            "hourly": {
                "time": times,
                "temperature_2m_ecmwf_ifs025": [-2.0] * 72,
                "precipitation_ecmwf_ifs025": [1.0] * 72,
                "snowfall_ecmwf_ifs025": [1.0] * 72,
                "wind_speed_10m_ecmwf_ifs025": [16.09344] * 72,
                "temperature_2m_gfs_hrrr": [-3.0] * 24 + [None] * 48,
                "precipitation_gfs_hrrr": [0.5] * 24 + [None] * 48,
                "snowfall_gfs_hrrr": [0.5] * 24 + [None] * 48,
            },
        }
        parsed = parse_multi_model_response(payload, ["ecmwf_ifs025", "gfs_hrrr"])

        ecmwf_hourly = parsed["models"]["ecmwf_ifs025"]["hourly"]
        self.assertEqual(len(ecmwf_hourly), 72)
        self.assertEqual(ecmwf_hourly[0]["time_utc"], "2026-11-14T00:00Z")
        self.assertAlmostEqual(ecmwf_hourly[0]["wind_mph"], 10.0)
        self.assertAlmostEqual(sum(r["snowfall_cm"] for r in ecmwf_hourly), 72.0)

        hrrr_hourly = parsed["models"]["gfs_hrrr"]["hourly"]
        self.assertEqual(sum(1 for r in hrrr_hourly if r["temp_c"] is not None), 24)
        self.assertIsNone(hrrr_hourly[24]["temp_c"])


class NwsParserTests(unittest.TestCase):
    def test_duration_and_layer_unit_normalization(self) -> None:
        self.assertEqual(parse_iso_duration("PT6H").total_seconds(), 21600)
        self.assertEqual(parse_iso_duration("P1DT12H").total_seconds(), 129600)

        payload = {
            "properties": {
                "gridId": "REV",
                "updateTime": "2026-11-14T00:00:00+00:00",
                "snowfallAmount": {
                    "uom": "wmoUnit:in",
                    "values": [
                        {"validTime": "2026-11-14T18:00:00+00:00/PT12H", "value": 5.0}
                    ],
                },
                "quantitativePrecipitation": {
                    "uom": "wmoUnit:mm",
                    "values": [
                        {"validTime": "2026-11-14T00:00:00+00:00/PT6H", "value": 10.0}
                    ],
                },
                "snowLevel": {
                    "uom": "wmoUnit:ft",
                    "values": [
                        {"validTime": "2026-11-14T00:00:00+00:00/PT6H", "value": 7000.0}
                    ],
                },
                "temperature": {
                    "uom": "wmoUnit:degC",
                    "values": [
                        {"validTime": "2026-11-14T00:00:00+00:00/PT1H", "value": -4.0}
                    ],
                },
            }
        }
        parsed = parse_grid_forecast_response(payload)
        snow_entry = parsed["layers"]["snowfall_amount_mm"][0]
        self.assertEqual(snow_entry["end_utc"], "2026-11-15T06:00:00+00:00")
        self.assertAlmostEqual(snow_entry["value"], 127.0)
        self.assertAlmostEqual(parsed["layers"]["snow_level_m"][0]["value"], 2133.6)
        self.assertAlmostEqual(parsed["layers"]["temperature_c"][0]["value"], -4.0)


class MetNoParserTests(unittest.TestCase):
    def test_met_no_hourly_to_6h_transition_no_double_counting(self) -> None:
        # 2 hourly steps followed by 1 six-hour step; each hourly entry also carries next_6_hours
        payload = {
            "geometry": {"type": "Point", "coordinates": [-120.1, 39.2, 2600]},
            "properties": {
                "meta": {"updated_at": "2026-11-14T00:00:00Z"},
                "timeseries": [
                    {
                        "time": "2026-11-14T00:00:00Z",
                        "data": {
                            "instant": {"details": {"air_temperature": -6.0, "wind_speed": 5.0}},
                            "next_1_hours": {"summary": {"symbol_code": "snow"}, "details": {"precipitation_amount": 2.0}},
                            "next_6_hours": {"summary": {"symbol_code": "snow"}, "details": {"precipitation_amount": 99.0}},
                        },
                    },
                    {
                        "time": "2026-11-14T01:00:00Z",
                        "data": {
                            "instant": {"details": {"air_temperature": -6.0, "wind_speed": 5.0}},
                            "next_1_hours": {"summary": {"symbol_code": "snow"}, "details": {"precipitation_amount": 3.0}},
                        },
                    },
                    {
                        "time": "2026-11-14T02:00:00Z",
                        "data": {
                            "instant": {"details": {"air_temperature": -6.0, "wind_speed": 5.0}},
                            "next_6_hours": {"summary": {"symbol_code": "snow"}, "details": {"precipitation_amount": 5.0}},
                        },
                    },
                    {
                        "time": "2026-11-14T08:00:00Z",
                        "data": {
                            "instant": {"details": {"air_temperature": -6.0, "wind_speed": 5.0}},
                            "next_6_hours": {"summary": {"symbol_code": "snow"}, "details": {"precipitation_amount": 10.0}},
                        },
                    },
                    {
                        "time": "2026-11-14T14:00:00Z",
                        "data": {
                            "instant": {"details": {"air_temperature": -6.0, "wind_speed": 5.0}},
                            "next_6_hours": {"summary": {"symbol_code": "snow"}, "details": {"precipitation_amount": 5.0}},
                        },
                    },
                    {
                        "time": "2026-11-14T20:00:00Z",
                        "data": {
                            "instant": {"details": {"air_temperature": -6.0, "wind_speed": 5.0}},
                            "next_6_hours": {"summary": {"symbol_code": "snow"}, "details": {"precipitation_amount": 0.0}},
                        },
                    },
                ],
            },
        }
        parsed = parse_met_no_response(payload)
        intervals = parsed["intervals"]
        self.assertEqual(intervals[0]["end_utc"], "2026-11-14T01:00:00+00:00")
        self.assertEqual(intervals[2]["end_utc"], "2026-11-14T08:00:00+00:00")
        # 2 + 3 + 5 + 10 + 5 = 25 mm precip (should NOT add the 99mm next_6_hours on hour 0)
        self.assertAlmostEqual(sum(iv["precip_mm"] for iv in intervals if iv["precip_mm"]), 25.0)
        # At -6 C, preliminary SLR is 13:1 -> 25 * 1.3 = 32.5 cm = 12.80 in
        self.assertAlmostEqual(sum(iv["est_snow_in"] for iv in intervals if iv["est_snow_in"]), 12.80, places=2)


class FetchSnapshotTests(unittest.TestCase):
    def test_fetch_all_data_parallel_isolation_and_open_meteo_circuit_breaker(self) -> None:
        resorts = [
            {
                "id": "us-resort",
                "name": "US Resort",
                "region": "Sierra",
                "state": "CA",
                "timezone": "America/Los_Angeles",
                "bands": {
                    "base": {
                        "label": "Base",
                        "lat": 38.68,
                        "lon": -120.06,
                        "reported_elevation_ft": 7800,
                        "reported_elevation_m": 2377.4,
                        "nws": {"forecast_grid_data_url": "https://api.weather.gov/gridpoints/STO/1,1"},
                    },
                    "summit": {
                        "label": "Summit",
                        "lat": 38.66,
                        "lon": -120.06,
                        "reported_elevation_ft": 9800,
                        "reported_elevation_m": 2987.0,
                        "nws": {"forecast_grid_data_url": "https://api.weather.gov/gridpoints/STO/2,2"},
                    },
                },
            },
            {
                "id": "bc-resort",
                "name": "BC Resort",
                "region": "Coast",
                "state": "BC",
                "timezone": "America/Vancouver",
                "bands": {
                    "base": {
                        "label": "Base",
                        "lat": 50.11,
                        "lon": -122.95,
                        "reported_elevation_ft": 2214,
                        "reported_elevation_m": 674.8,
                        "nws": None,
                    },
                    "summit": {
                        "label": "Summit",
                        "lat": 50.06,
                        "lon": -122.96,
                        "reported_elevation_ft": 7160,
                        "reported_elevation_m": 2182.4,
                        "nws": None,
                    },
                },
            },
        ]

        om_calls: list[float] = []

        def fake_om(lat: float, lon: float, elevation_m: float | None = None, **kwargs: object) -> dict[str, object]:
            om_calls.append(lat)
            if len(om_calls) >= 2:
                raise HttpFetchError("429 too many requests")
            return {"source": "open-meteo", "models": {}}

        def fake_met(lat: float, lon: float, elevation_m: float | None = None) -> dict[str, object]:
            if lat > 45.0:
                raise HttpFetchError("met timeout")
            return {"source": "met-no", "intervals": []}

        def fake_nws(url: str) -> dict[str, object]:
            return {"source": "nws-gridpoints", "url": url, "layers": {}}

        with (
            patch("app.scripts.fetch_snapshot.fetch_multi_model_forecast", side_effect=fake_om),
            patch("app.scripts.fetch_snapshot.fetch_met_no_forecast", side_effect=fake_met),
            patch("app.scripts.fetch_snapshot.fetch_grid_forecast", side_effect=fake_nws),
            patch(
                "app.scripts.fetch_snapshot.fetch_current_snowpack_for_resorts",
                return_value={"us-resort": {"status": "ok", "stations": []}},
            ),
        ):
            snap = fetch_all_data(resorts, bands=("base", "summit"), models=("ecmwf_ifs025",))

        # Circuit breaker halts Open-Meteo calls after the first failure (called twice, skipped 2 remaining)
        self.assertEqual(len(om_calls), 2)
        self.assertEqual([r["id"] for r in snap["resorts"]], ["us-resort", "bc-resort"])

        us_res, bc_res = snap["resorts"]
        self.assertEqual(us_res["current_snowpack"]["status"], "ok")
        self.assertIsNone(bc_res["current_snowpack"])
        self.assertEqual(us_res["bands"]["base"]["open_meteo"]["status"], "ok")
        self.assertEqual(us_res["bands"]["summit"]["open_meteo"]["status"], "unavailable")
        self.assertEqual(bc_res["bands"]["base"]["open_meteo"]["status"], "unavailable")
        self.assertEqual(us_res["bands"]["base"]["met_no"]["status"], "ok")
        self.assertEqual(bc_res["bands"]["base"]["met_no"]["status"], "unavailable")
        self.assertEqual(us_res["bands"]["summit"]["nws"]["status"], "ok")
        self.assertIsNone(bc_res["bands"]["base"]["nws"])


if __name__ == "__main__":
    unittest.main()
