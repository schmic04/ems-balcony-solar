# Copyright (c) 2019-2025 Michael Schmidt @schmic04
"""Fixtures for ems_balcony_solar tests."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ems_balcony_solar.const import CONF_SENSOR, DOMAIN

if TYPE_CHECKING:
    from collections.abc import Generator

SOURCE_SENSOR = "sensor.price_source"

# 96 quarter-hour prices (ct/kWh) with three distinct peaks.
PRICES_TODAY = (
    [10.0 + (i % 8) for i in range(32)]
    + [30.0 - abs(i - 16) for i in range(32)]
    + [12.0 + (i % 6) for i in range(32)]
)


@pytest.fixture(autouse=True)
def mock_api() -> Generator[None]:
    """Avoid network access of the sample API client."""
    with patch(
        "custom_components.ems_balcony_solar.api."
        "EMSBalconySolarApiClient.async_get_data",
        return_value={},
    ):
        yield


@pytest.fixture
def config_entry() -> MockConfigEntry:
    """Return a config entry that uses a mocked Nord Pool style source sensor."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="EMS Balcony Solar",
        unique_id=DOMAIN,
        data={CONF_SENSOR: SOURCE_SENSOR},
    )
