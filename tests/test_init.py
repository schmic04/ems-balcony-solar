# Copyright (c) 2019-2025 Michael Schmidt @schmic04
# ruff: noqa: S101
"""Tests for setup, unload and reload of the integration."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from homeassistant.config_entries import ConfigEntryState

from .conftest import PRICES_TODAY, SOURCE_SENSOR

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from pytest_homeassistant_custom_component.common import MockConfigEntry

# The manifest depends on recorder, so a mocked recorder must run before hass.
pytestmark = pytest.mark.usefixtures("recorder_mock", "enable_custom_integrations")

PRICE_SENSOR = "sensor.current_electricity_price"
BINARY_SENSOR = "binary_sensor.price_range_active"
EXPECTED_ENTITIES = (
    PRICE_SENSOR,
    BINARY_SENSOR,
    "number.sublist_length",
    "number.number_of_sublists",
    "switch.ems_balcony_solar",
    "switch.debugging",
)


async def _setup(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    """Provide a source sensor and set up the config entry."""
    hass.states.async_set(
        SOURCE_SENSOR, "10", {"today": PRICES_TODAY, "tomorrow_valid": False}
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


async def test_setup_creates_entities(
    hass: HomeAssistant, config_entry: MockConfigEntry
) -> None:
    """All entities exist with the entity ids the code relies on."""
    await _setup(hass, config_entry)

    assert config_entry.state is ConfigEntryState.LOADED
    for entity_id in EXPECTED_ENTITIES:
        assert hass.states.get(entity_id) is not None, entity_id


async def test_unload(hass: HomeAssistant, config_entry: MockConfigEntry) -> None:
    """Unloading must not raise and must remove the entities."""
    await _setup(hass, config_entry)

    assert await hass.config_entries.async_unload(config_entry.entry_id)
    await hass.async_block_till_done()

    assert config_entry.state is ConfigEntryState.NOT_LOADED
    assert hass.states.get(PRICE_SENSOR).state == "unavailable"


async def test_reload_keeps_sensor_alive(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """
    Regression: reload must not leave a stale sensor behind.

    Unloading used to raise AttributeError, the old sensor stayed registered and
    the new one was rejected as duplicate unique_id.
    """
    await _setup(hass, config_entry)

    assert await hass.config_entries.async_reload(config_entry.entry_id)
    await hass.async_block_till_done()

    assert config_entry.state is ConfigEntryState.LOADED
    assert "AttributeError" not in caplog.text
    assert "does not generate unique IDs" not in caplog.text
    assert hass.states.get(PRICE_SENSOR).state != "unavailable"

    # The new sensor instance must react to changes of its inputs again.
    await hass.services.async_call(
        "number",
        "set_value",
        {"entity_id": "number.sublist_length", "value": 16},
        blocking=True,
    )
    await hass.services.async_call(
        "number",
        "set_value",
        {"entity_id": "number.number_of_sublists", "value": 3},
        blocking=True,
    )
    await hass.async_block_till_done()

    attributes = hass.states.get(PRICE_SENSOR).attributes
    assert attributes["price_list_count"] == len(PRICES_TODAY)
    assert attributes["price_sublists_count"] > 0
    assert attributes["price_sublists_time_ranges"]
