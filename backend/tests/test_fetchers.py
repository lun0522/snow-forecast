"""Offline unit tests for geo helpers and Open-Meteo, NWS, SNOTEL, and CDEC parsers."""

from __future__ import annotations

import unittest
from datetime import datetime, timezone

from app.fetchers.cdec import parse_cdec_sensor_rows
from app.fetchers.met_no import parse_met_no_response
from app.fetchers.nws import parse_grid_forecast_response, parse_iso_duration
from app.fetchers.open_meteo import parse_multi_model_response
from app.fetchers.snotel import find_nearest_snotel_stations, parse_snotel_data_response
from app.geo import haversine_km


class GeoTests(unittest.TestCase):
    def test_haversine_known_distance(self) -> None:
        # Kirkwood base to Heavenly base is roughly 30 km
        dist = haversine_km(38.6840, -120.0680, 38.9353, -119.9400)
        self.assertGreater(dist, 28.0)
        self.assertLess(dist, 33.0)


class OpenMeteoParserTests(unittest.TestCase):
    def test_multi_model_partial_horizon_handling(self) -> None:
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
                "snowfall_ecmwf_ifs025": [1.0] * 72,  # 72 cm total over 72h
                "temperature_2m_gfs_hrrr": [-3.0] * 24 + [None] * 48,
                "precipitation_gfs_hrrr": [0.5] * 24 + [None] * 48,
                "snowfall_gfs_hrrr": [0.5] * 24 + [None] * 48,
            },
        }
        ref = datetime(2026, 11, 14, 0, 0, tzinfo=timezone.utc)
        parsed = parse_multi_model_response(payload, ["ecmwf_ifs025", "gfs_hrrr"], reference_time=ref)

        ecmwf_summary = parsed["models"]["ecmwf_ifs025"]["summary"]
        self.assertEqual(ecmwf_summary["max_horizon_hours"], 72)
        self.assertIn("24h", ecmwf_summary["windows"])
        self.assertIn("72h", ecmwf_summary["windows"])
        self.assertAlmostEqual(ecmwf_summary["windows"]["72h"]["snowfall_cm"], 72.0)

        hrrr_summary = parsed["models"]["gfs_hrrr"]["summary"]
        self.assertEqual(hrrr_summary["max_horizon_hours"], 24)
        self.assertIn("24h", hrrr_summary["windows"])
        self.assertNotIn("72h", hrrr_summary["windows"])


class NwsParserTests(unittest.TestCase):
    def test_duration_and_overlapping_interval_apportionment(self) -> None:
        self.assertEqual(parse_iso_duration("PT6H").total_seconds(), 21600)
        self.assertEqual(parse_iso_duration("P1DT12H").total_seconds(), 129600)

        payload = {
            "properties": {
                "gridId": "REV",
                "updateTime": "2026-11-14T00:00:00+00:00",
                "elevation": {"value": 2500.0, "unitCode": "wmoUnit:m"},
                "snowfallAmount": {
                    "uom": "wmoUnit:mm",
                    "values": [
                        # 12h interval straddling the 24h boundary: 18:00 -> 06:00 next day
                        {"validTime": "2026-11-14T18:00:00+00:00/PT12H", "value": 120.0}
                    ],
                },
                "quantitativePrecipitation": {
                    "uom": "wmoUnit:mm",
                    "values": [
                        {"validTime": "2026-11-14T00:00:00+00:00/PT6H", "value": 10.0}
                    ],
                },
                "snowLevel": {
                    "uom": "wmoUnit:m",
                    "values": [
                        {"validTime": "2026-11-14T00:00:00+00:00/PT6H", "value": 2100.0}
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
        ref = datetime(2026, 11, 14, 0, 0, tzinfo=timezone.utc)
        parsed = parse_grid_forecast_response(payload, reference_time=ref)
        # Half of the 12h 120mm snowfall falls in the first 24h -> 60mm
        self.assertAlmostEqual(parsed["windows"]["24h"]["snowfall_mm"], 60.0)
        self.assertAlmostEqual(parsed["windows"]["48h"]["snowfall_mm"], 120.0)
        self.assertAlmostEqual(parsed["windows"]["24h"]["temp_min_f"], 24.8)


class SnotelAndCdecTests(unittest.TestCase):
    def test_snotel_nearest_and_delta_calculation(self) -> None:
        stations = [
            {
                "stationTriplet": "518:CA:SNTL",
                "name": "Heavenly Valley",
                "latitude": 38.92,
                "longitude": -119.92,
                "elevation": 8540,
                "stateCode": "CA",
            },
            {
                "stationTriplet": "505:CO:SNTL",
                "name": "Grizzly Peak",
                "latitude": 39.65,
                "longitude": -105.87,
                "elevation": 11110,
                "stateCode": "CO",
            },
        ]
        nearest = find_nearest_snotel_stations(38.929, -119.919, stations, limit=2, max_distance_km=50.0)
        self.assertEqual(len(nearest), 1)
        self.assertEqual(nearest[0]["triplet"], "518:CA:SNTL")

        raw_data = [
            {
                "stationTriplet": "518:CA:SNTL",
                "data": [
                    {
                        "stationElement": {"elementCode": "WTEQ", "storedUnitCode": "in"},
                        "values": [
                            {"date": "2026-11-12", "value": 2.0},
                            {"date": "2026-11-13", "value": 2.8},
                        ],
                    },
                    {
                        "stationElement": {"elementCode": "SNWD", "storedUnitCode": "in"},
                        "values": [
                            {"date": "2026-11-12", "value": 10.0},
                            {"date": "2026-11-13", "value": 18.0},
                        ],
                    },
                ],
            }
        ]
        parsed = parse_snotel_data_response(raw_data)
        summary = parsed["518:CA:SNTL"]["summary"]
        self.assertEqual(summary["cadence"], "DAILY")
        self.assertAlmostEqual(summary["swe_in"], 2.8)
        self.assertAlmostEqual(summary["swe_delta_24h_in"], 0.8)
        self.assertAlmostEqual(summary["snow_depth_delta_24h_in"], 8.0)

    def test_cdec_filters_sentinels_and_normalizes_dates(self) -> None:
        rows = [
            {"SENSOR_NUM": 3, "date": "2026-11-12 00:00", "value": -9999, "units": "INCHES"},
            {"SENSOR_NUM": 3, "date": "2026-11-9 00:00", "value": -0.28, "units": "INCHES"},
            {"SENSOR_NUM": 18, "date": "2026-11-13 00:00", "value": "---", "units": "INCHES"},
            {"SENSOR_NUM": 18, "date": "2026-11-13 00:00", "value": 14.5, "units": "INCHES"},
        ]
        cleaned = parse_cdec_sensor_rows(rows)
        self.assertEqual(len(cleaned), 2)
        self.assertEqual(cleaned[0]["timestamp"], "2026-11-09 00:00")
        self.assertEqual(cleaned[0]["metric"], "swe_in")
        self.assertAlmostEqual(cleaned[0]["value"], 0.0)
        self.assertEqual(cleaned[1]["metric"], "snow_depth_in")
        self.assertAlmostEqual(cleaned[1]["value"], 14.5)
        self.assertLess(cleaned[0]["timestamp"], cleaned[1]["timestamp"])


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
        ref = datetime(2026, 11, 14, 0, 0, tzinfo=timezone.utc)
        parsed = parse_met_no_response(payload, reference_time=ref)
        # 2 + 3 + 5 + 10 + 5 = 25 mm precip (should NOT add the 99mm next_6_hours on hour 0)
        self.assertAlmostEqual(parsed["windows"]["24h"]["precip_mm"], 25.0)
        # At -6 C, preliminary SLR is 13:1 -> 25 * 1.3 = 32.5 cm
        self.assertAlmostEqual(parsed["windows"]["24h"]["est_snow_cm"], 32.5)


if __name__ == "__main__":
    unittest.main()
