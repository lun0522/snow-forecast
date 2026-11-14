"""Geospatial and unit conversion helpers."""

from __future__ import annotations

import math

EARTH_RADIUS_KM = 6371.0088


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return great-circle distance in kilometers between two WGS84 coordinates."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lam = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lam / 2.0) ** 2
    return 2.0 * EARTH_RADIUS_KM * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))


def feet_to_meters(feet: float) -> float:
    """Convert feet to meters."""
    return feet * 0.3048


def meters_to_feet(meters: float) -> float:
    """Convert meters to feet."""
    return meters / 0.3048


def mm_to_inches(mm: float) -> float:
    """Convert millimeters to inches."""
    return mm / 25.4


def cm_to_inches(cm: float) -> float:
    """Convert centimeters to inches."""
    return cm / 2.54


def c_to_f(celsius: float) -> float:
    """Convert Celsius to Fahrenheit."""
    return celsius * 9.0 / 5.0 + 32.0


def kph_to_mph(kph: float) -> float:
    """Convert kilometers per hour to miles per hour."""
    return kph * 0.62137119
