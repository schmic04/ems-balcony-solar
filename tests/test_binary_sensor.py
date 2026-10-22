"""Tests for the price range binary sensor."""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING

import pytest
from homeassistant.util import dt as dt_util

from custom_components.ems_balcony_solar.price_list_api import (
    convert_indices_to_time_ranges,
)

from .test_init import BINARY_SENSOR, PRICE_SENSOR, _setup

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from pytest_homeassistant_custom_component.common import MockConfigEntry

# The manifest depends on recorder, so a mocked recorder must run before hass.
pytestmark = pytest.mark.usefixtures("recorder_mock", "enable_custom_integrations")


async def test_next_range_and_active_range(
    hass: HomeAssistant, config_entry: MockConfigEntry
) -> None:
    """next_range and active_range follow the time ranges of the price sensor."""
    await _setup(hass, config_entry)

    now = dt_util.now().replace(second=0, microsecond=0)
    base = now.replace(hour=0, minute=0)
    quarter = int((now - base) / timedelta(minutes=15))
    # One range containing "now" and one range in the future (same day or later).
    ranges = convert_indices_to_time_ranges(
        [[quarter, quarter + 1], [quarter + 8, quarter + 9]], base
    )

    hass.states.async_set(
        PRICE_SENSOR,
        "10",
        {"price_sublists_time_ranges": ranges, "last_update": now.isoformat()},
    )
    await hass.async_block_till_done()

    state = hass.states.get(BINARY_SENSOR)
    assert state.state == "on"
    assert state.attributes["active_range"] == ranges[0][0]
    assert state.attributes["next_range"] == ranges[1][0]


async def test_inactive_without_ranges(
    hass: HomeAssistant, config_entry: MockConfigEntry
) -> None:
    """Without time ranges the sensor is off and has no next range."""
    await _setup(hass, config_entry)

    state = hass.states.get(BINARY_SENSOR)
    assert state.state == "off"
    assert state.attributes["next_range"] is None
