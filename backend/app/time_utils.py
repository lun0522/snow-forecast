"""Shared UTC timestamp helpers."""

from __future__ import annotations

from datetime import datetime, timezone


def parse_utc(ts: str) -> datetime:
    """Parse an ISO-8601 timestamp string as an aware UTC datetime."""
    dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def floor_utc_hour(dt: datetime) -> datetime:
    """Floor an aware datetime to the start of its UTC hour."""
    return dt.astimezone(timezone.utc).replace(minute=0, second=0, microsecond=0)
