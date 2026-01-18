"""Utility functions for Watts Vision integration."""

from datetime import timedelta


def timedelta_to_dict(value: timedelta) -> dict:
    """Convert a timedelta to a dictionary with hours, minutes, and seconds."""

    total_seconds = int(value.total_seconds())
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return {"hours": hours, "minutes": minutes, "seconds": seconds}


def clamp(n: float, smallest: float, largest: float) -> float:
    """Clamp a number between a smallest and largest value."""

    return max(smallest, min(n, largest))
