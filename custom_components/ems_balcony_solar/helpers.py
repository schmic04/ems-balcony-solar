# Copyright (c) 2019-2025 Michael Schmidt @schmic04
"""Helper functions for EMS Balcony Solar."""

from __future__ import annotations

import secrets


def get_random_value() -> float:
    """
    Generate a random value for the sensor.

    Returns a random float between 0 and 100.
    """
    return round(secrets.randbelow(10000) / 100.0, 2)
