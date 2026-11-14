"""Static seed definitions for tracked ski resorts."""

from __future__ import annotations

from typing import Any

from app.geo import feet_to_meters

SEED_RESORTS: list[dict[str, Any]] = [
    {
        "id": "northstar",
        "name": "Northstar California",
        "region": "North Lake Tahoe",
        "state": "CA",
        "timezone": "America/Los_Angeles",
        "bands": {
            "base": {
                "label": "Village Base",
                "lat": 39.2747,
                "lon": -120.1211,
                "reported_elevation_ft": 6330,
                "reported_elevation_m": round(feet_to_meters(6330), 1),
            },
            "mid": {
                "label": "Mid-Mountain",
                "lat": 39.2582,
                "lon": -120.1304,
                "reported_elevation_ft": 7470,
                "reported_elevation_m": round(feet_to_meters(7470), 1),
            },
            "summit": {
                "label": "Mt. Pluto Summit",
                "lat": 39.2416,
                "lon": -120.1396,
                "reported_elevation_ft": 8610,
                "reported_elevation_m": round(feet_to_meters(8610), 1),
            },
        },
    },
    {
        "id": "heavenly",
        "name": "Heavenly Mountain",
        "region": "South Lake Tahoe",
        "state": "CA",
        "timezone": "America/Los_Angeles",
        "bands": {
            "base": {
                "label": "California Base",
                "lat": 38.9353,
                "lon": -119.9400,
                "reported_elevation_ft": 6255,
                "reported_elevation_m": round(feet_to_meters(6255), 1),
            },
            "mid": {
                "label": "Mid-Mountain",
                "lat": 38.9290,
                "lon": -119.9190,
                "reported_elevation_ft": 8160,
                "reported_elevation_m": round(feet_to_meters(8160), 1),
            },
            "summit": {
                "label": "Monument Peak Summit",
                "lat": 38.9227,
                "lon": -119.8978,
                "reported_elevation_ft": 10067,
                "reported_elevation_m": round(feet_to_meters(10067), 1),
            },
        },
    },
    {
        "id": "kirkwood",
        "name": "Kirkwood Mountain",
        "region": "Sierra Crest",
        "state": "CA",
        "timezone": "America/Los_Angeles",
        "bands": {
            "base": {
                "label": "Mountain Village Base",
                "lat": 38.6840,
                "lon": -120.0680,
                "reported_elevation_ft": 7800,
                "reported_elevation_m": round(feet_to_meters(7800), 1),
            },
            "mid": {
                "label": "Mid-Mountain",
                "lat": 38.6732,
                "lon": -120.0643,
                "reported_elevation_ft": 8800,
                "reported_elevation_m": round(feet_to_meters(8800), 1),
            },
            "summit": {
                "label": "Thimble Peak Summit",
                "lat": 38.6624,
                "lon": -120.0605,
                "reported_elevation_ft": 9800,
                "reported_elevation_m": round(feet_to_meters(9800), 1),
            },
        },
    },
    {
        "id": "park-city",
        "name": "Park City Mountain",
        "region": "Wasatch Back",
        "state": "UT",
        "timezone": "America/Denver",
        "bands": {
            "base": {
                "label": "Park City Base",
                "lat": 40.6508,
                "lon": -111.5075,
                "reported_elevation_ft": 6800,
                "reported_elevation_m": round(feet_to_meters(6800), 1),
            },
            "mid": {
                "label": "Mid-Mountain",
                "lat": 40.6321,
                "lon": -111.5221,
                "reported_elevation_ft": 8413,
                "reported_elevation_m": round(feet_to_meters(8413), 1),
            },
            "summit": {
                "label": "Jupiter Peak Summit",
                "lat": 40.6133,
                "lon": -111.5367,
                "reported_elevation_ft": 10026,
                "reported_elevation_m": round(feet_to_meters(10026), 1),
            },
        },
    },
    {
        "id": "keystone",
        "name": "Keystone Resort",
        "region": "Summit County",
        "state": "CO",
        "timezone": "America/Denver",
        "bands": {
            "base": {
                "label": "River Run Base",
                "lat": 39.6050,
                "lon": -105.9542,
                "reported_elevation_ft": 9280,
                "reported_elevation_m": round(feet_to_meters(9280), 1),
            },
            "mid": {
                "label": "Mid-Mountain (Dercum)",
                "lat": 39.5792,
                "lon": -105.9411,
                "reported_elevation_ft": 11640,
                "reported_elevation_m": round(feet_to_meters(11640), 1),
            },
            "summit": {
                "label": "Bergman / Independence Ridge",
                "lat": 39.5816,
                "lon": -105.9101,
                "reported_elevation_ft": 12408,
                "reported_elevation_m": round(feet_to_meters(12408), 1),
            },
        },
    },
    {
        "id": "whistler-blackcomb",
        "name": "Whistler Blackcomb",
        "region": "Coast Mountains",
        "state": "BC",
        "timezone": "America/Vancouver",
        "bands": {
            "base": {
                "label": "Whistler Village Base",
                "lat": 50.1128,
                "lon": -122.9543,
                "reported_elevation_ft": 2214,
                "reported_elevation_m": round(feet_to_meters(2214), 1),
            },
            "mid": {
                "label": "Roundhouse Lodge",
                "lat": 50.0696,
                "lon": -122.9465,
                "reported_elevation_ft": 6069,
                "reported_elevation_m": round(feet_to_meters(6069), 1),
            },
            "summit": {
                "label": "Whistler Peak",
                "lat": 50.0591,
                "lon": -122.9569,
                "reported_elevation_ft": 7160,
                "reported_elevation_m": round(feet_to_meters(7160), 1),
            },
        },
    },
]
