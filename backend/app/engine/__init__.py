"""Step 3: Snow physics, hourly normalization, and multi-model consensus blending."""

from app.engine.blending import process_resort_snapshot, process_snapshot
from app.engine.physics import (
    apply_snowpack_settling,
    classify_snow_fraction,
    compute_dynamic_slr,
    compute_hourly_physics_snow,
    compute_snow_fraction,
    compute_wet_bulb_c,
)

__all__ = [
    "apply_snowpack_settling",
    "classify_snow_fraction",
    "compute_dynamic_slr",
    "compute_hourly_physics_snow",
    "compute_snow_fraction",
    "compute_wet_bulb_c",
    "process_resort_snapshot",
    "process_snapshot",
]
