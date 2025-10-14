"""Helper functions for EMS Balcony Solar."""

from __future__ import annotations

import random


def get_random_value() -> float:
    """Generate a random value for the sensor.
    
    Returns a random float between 0 and 100.
    """
    return round(random.uniform(0, 100), 2)
