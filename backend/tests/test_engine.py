"""Unit tests for Step 3 snow physics, compaction, timeline alignment, and consensus blending."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import unittest

from app.engine.blending import process_snapshot
from app.engine.physics import (
    apply_snowpack_settling,
    classify_snow_fraction,
    compute_dynamic_slr,
    compute_hourly_physics_snow,
    compute_snow_fraction,
    compute_wet_bulb_c,
)


class PhysicsTests(unittest.TestCase):
    def test_wet_bulb_cooler_than_dry_bulb_in_dry_air(self) -> None:
        # At +2.0 C and 35% RH, evaporative cooling pulls wet-bulb well below 0 C.
        tw = compute_wet_bulb_c(2.0, 35.0)
        self.assertIsNotNone(tw)
        assert tw is not None
        self.assertLess(tw, -1.5)
        self.assertAlmostEqual(compute_wet_bulb_c(2.0, None) or 0.0, 2.0)

    def test_snow_fraction_thermal_and_elevation_risk(self) -> None:
        self.assertEqual(compute_snow_fraction(-2.5, band_elevation_m=2500, snow_level_m=1800), 1.0)
        self.assertEqual(compute_snow_fraction(3.2, band_elevation_m=2000, snow_level_m=2500), 0.0)

        mix = compute_snow_fraction(0.8, band_elevation_m=2100, snow_level_m=2100)
        self.assertGreater(mix, 0.2)
        self.assertLess(mix, 0.8)
        self.assertEqual(classify_snow_fraction(mix), "mixed")

    def test_dynamic_slr_temperature_curve_and_wind_compaction(self) -> None:
        warm_slr = compute_dynamic_slr(0.5, wind_mph=5.0)
        cold_calm_slr = compute_dynamic_slr(-12.0, wind_mph=5.0)
        cold_windy_slr = compute_dynamic_slr(-12.0, wind_mph=35.0)

        self.assertAlmostEqual(warm_slr, 8.0, delta=0.2)
        self.assertAlmostEqual(cold_calm_slr, 18.5, delta=0.2)
        self.assertLess(cold_windy_slr, cold_calm_slr * 0.75)

    def test_hourly_physics_snow_unit_conversion(self) -> None:
        # 25.4 mm liquid at 10:1 calm cold conditions -> 10.0 inches of snow
        res = compute_hourly_physics_snow(
            precip_mm=25.4,
            temp_c=-3.0,
            rh_pct=90.0,
            wind_mph=5.0,
        )
        self.assertEqual(res["snow_fraction"], 1.0)
        self.assertGreater(float(res["slr"] or 0.0), 11.0)
        self.assertAlmostEqual(float(res["physics_snow_in"] or 0.0), float(res["slr"]), places=2)

    def test_snowpack_settling_compacts_over_time(self) -> None:
        snow = [2.0] * 12 + [0.0] * 12
        temps = [-4.0] * 24
        settled = apply_snowpack_settling(snow, temps)
        self.assertEqual(len(settled), 24)
        self.assertLess(settled[11], 24.0)
        self.assertLess(settled[23], settled[11])


class BlendingTests(unittest.TestCase):
    def _build_synthetic_snapshot(self) -> dict:
        anchor = datetime(2026, 11, 14, 8, 0, tzinfo=timezone.utc)  # 00:00 PST on Nov 14

        def make_om_rows(hours: int, precip_mm_each: float, temp_c: float, rh_pct: float = 90.0) -> list[dict]:
            rows = []
            for h in range(hours):
                t = anchor + timedelta(hours=h)
                rows.append(
                    {
                        "time_utc": t.isoformat(),
                        "temp_c": temp_c,
                        "temp_f": temp_c * 9.0 / 5.0 + 32.0,
                        "rh_pct": rh_pct,
                        "precip_mm": precip_mm_each,
                        "precip_in": precip_mm_each / 25.4,
                        "rain_mm": 0.0,
                        "snowfall_cm": precip_mm_each / 10.0,
                        "snowfall_in": (precip_mm_each / 10.0) / 2.54,
                        "freezing_level_m": 2000.0,
                        "wind_mph": 10.0,
                        "wind_gust_mph": 18.0,
                        "wind_dir_deg": 240.0,
                    }
                )
            return rows

        # Create 72h synthetic storm in hours 0..23 so 24h/48h/72h windows & day 1 capture it
        ecmwf_rows = make_om_rows(168, 0.0, -5.0)
        gfs_rows = make_om_rows(168, 0.0, -5.0)
        hrrr_rows = make_om_rows(44, 0.0, -5.0) + [
            {"time_utc": (anchor + timedelta(hours=h)).isoformat(), "temp_c": None, "precip_mm": None, "snowfall_cm": None}
            for h in range(44, 168)
        ]
        for h in range(10):
            ecmwf_rows[h]["precip_mm"] = 2.54
            gfs_rows[h]["precip_mm"] = 5.08
            hrrr_rows[h]["precip_mm"] = 3.81

        # Add MET Norway 6h block during day 2 (hours 24..30) with 6.0 mm total -> 1.0 mm/hr
        met_intervals = []
        for b_start in range(0, 168, 6):
            t0 = anchor + timedelta(hours=b_start)
            t1 = t0 + timedelta(hours=6)
            p_mm = 6.0 if b_start == 24 else 0.0
            met_intervals.append(
                {
                    "start_utc": t0.isoformat(),
                    "end_utc": t1.isoformat(),
                    "step_hours": 6.0,
                    "temp_c": -6.0,
                    "rh_pct": 88.0,
                    "wind_mph": 8.0,
                    "wind_gust_mph": 14.0,
                    "wind_dir_deg": 250.0,
                    "precip_mm": p_mm,
                    "est_snow_in": p_mm * 0.4,
                    "pop_pct": 80.0,
                }
            )

        # NWS 6h layer for summit matching 168h
        nws_qpf = []
        nws_temp = []
        nws_snow_lvl = []
        for b_start in range(0, 168, 6):
            t0 = (anchor + timedelta(hours=b_start)).isoformat()
            t1 = (anchor + timedelta(hours=b_start + 6)).isoformat()
            nws_qpf.append({"start_utc": t0, "end_utc": t1, "value": 6.0 if b_start == 0 else 0.0})
            nws_temp.append({"start_utc": t0, "end_utc": t1, "value": -4.0})
            nws_snow_lvl.append({"start_utc": t0, "end_utc": t1, "value": 1800.0})

        return {
            "fetched_at_utc": anchor.isoformat(),
            "models_requested": ["ecmwf_ifs025", "gfs_global", "gfs_hrrr"],
            "resorts": [
                {
                    "id": "kirkwood",
                    "name": "Kirkwood Mountain",
                    "region": "Lake Tahoe",
                    "state": "CA",
                    "timezone": "America/Los_Angeles",
                    "bands": {
                        "summit": {
                            "label": "Summit",
                            "elevation_ft": 9800,
                            "elevation_m": 2987.0,
                            "open_meteo": {
                                "status": "ok",
                                "models": {
                                    "ecmwf_ifs025": {"hourly": ecmwf_rows},
                                    "gfs_global": {"hourly": gfs_rows},
                                    "gfs_hrrr": {"hourly": hrrr_rows},
                                },
                            },
                            "met_no": {"status": "ok", "intervals": met_intervals},
                            "nws": {
                                "status": "ok",
                                "layers": {
                                    "quantitative_precipitation_mm": nws_qpf,
                                    "snowfall_amount_mm": nws_qpf,
                                    "temperature_c": nws_temp,
                                    "snow_level_m": nws_snow_lvl,
                                    "wind_speed_kph": [],
                                    "wind_gust_kph": [],
                                    "probability_of_precipitation_pct": [],
                                },
                            },
                        }
                    },
                }
            ],
        }

    def test_partial_horizon_exclusion_and_interval_alignment(self) -> None:
        processed = process_snapshot(self._build_synthetic_snapshot())
        summit = processed["resorts"][0]["bands"]["summit"]

        # HRRR (44h) must contribute to 24h consensus, but NOT 72h/168h consensus!
        self.assertIn("gfs_hrrr", summit["windows"]["24h"]["models_used"])
        self.assertNotIn("gfs_hrrr", summit["windows"]["72h"]["models_used"])
        self.assertNotIn("gfs_hrrr", summit["windows"]["168h"]["models_used"])
        self.assertIn("nws_gridpoints", summit["windows"]["168h"]["models_used"])
        self.assertIn("met_no", summit["windows"]["168h"]["models_used"])

        # MET Norway 6h block (hours 24..29) splits 6.0mm evenly -> ~0.0394 in/hr
        met_hourly = summit["models"]["met_no"]["hourly"]
        for idx in range(24, 30):
            self.assertAlmostEqual(met_hourly[idx]["precip_in"], 1.0 / 25.4, places=2)
            self.assertGreater(met_hourly[idx]["physics_snow_in"], 0.4)

        # Anchor 08:00Z = 00:00 PST on Nov 14 -> first 24 hours stay in 2026-11-14 local date bucket
        day1 = summit["daily"][0]
        self.assertEqual(day1["date"], "2026-11-14")
        self.assertEqual(day1["hours_in_bucket"], 24)
        self.assertFalse(day1["is_partial"])

        # Consensus invariants: min <= median <= max
        w24 = summit["windows"]["24h"]
        self.assertLessEqual(w24["snow_min_in"], w24["snow_median_in"])
        self.assertLessEqual(w24["snow_median_in"], w24["snow_max_in"])
        self.assertEqual(w24["rain_snow_risk"], "snow")

    def test_zero_coverage_model_and_missing_nws_omitted_cleanly(self) -> None:
        snap = self._build_synthetic_snapshot()
        band = snap["resorts"][0]["bands"]["summit"]
        band["nws"] = None
        band["open_meteo"]["models"]["gfs_hrrr"]["hourly"] = [
            {"time_utc": row["time_utc"], "temp_c": None, "precip_mm": None, "snowfall_cm": None}
            for row in band["open_meteo"]["models"]["ecmwf_ifs025"]["hourly"]
        ]
        processed = process_snapshot(snap)
        summit = processed["resorts"][0]["bands"]["summit"]

        self.assertNotIn("gfs_hrrr", summit["models"])
        self.assertNotIn("nws_gridpoints", summit["models"])
        self.assertNotIn("gfs_hrrr", summit["windows"]["24h"]["models_used"])
        self.assertIn("ecmwf_ifs025", summit["windows"]["24h"]["models_used"])


if __name__ == "__main__":
    unittest.main()
