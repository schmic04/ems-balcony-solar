"""Tests for the pure functions of price_list_api."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

import pytest

from custom_components.ems_balcony_solar.price_list_api import (
    convert_indices_to_time_ranges,
    get_combined_price_list,
    group_prices_by_hour,
    parse_time_range_to_timestamps,
    split_price_list,
)

from .conftest import PRICES_TODAY

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

TZ = timezone(timedelta(hours=2))
BASE = datetime(2026, 10, 22, 0, 0, tzinfo=TZ)


def test_convert_indices_groups_consecutive_indices() -> None:
    """Consecutive indices become one range, gaps start a new one."""
    assert convert_indices_to_time_ranges([[16, 17, 18, 22]], BASE) == [
        ["04:00+00-04:45+00", "05:30+00-05:45+00"]
    ]


def test_convert_indices_day_offset() -> None:
    """Ranges crossing midnight carry a day offset."""
    assert convert_indices_to_time_ranges([[92, 93, 94, 95, 96, 97]], BASE) == [
        ["23:00+00-00:30+01"]
    ]


def test_convert_indices_empty() -> None:
    """Empty input yields empty output."""
    assert convert_indices_to_time_ranges([], BASE) == []
    assert convert_indices_to_time_ranges([[]], BASE) == [[]]


def test_parse_time_range_roundtrip() -> None:
    """A formatted range parses back to the original timestamps."""
    start, end = parse_time_range_to_timestamps("23:00+00-01:00+01", BASE)
    assert start == BASE.replace(hour=23)
    assert end == BASE.replace(hour=1) + timedelta(days=1)


def test_parse_time_range_legacy_format_wraps_midnight() -> None:
    """The legacy format without offsets moves an earlier end to the next day."""
    start, end = parse_time_range_to_timestamps("23:00-01:00", BASE)
    assert end - start == timedelta(hours=2)


@pytest.mark.parametrize(
    "value", ["", "garbage", "10:00", "10:00-11:00-12:00", "xx:yy-aa:bb"]
)
def test_parse_time_range_invalid(value: str) -> None:
    """Invalid input raises ValueError."""
    with pytest.raises(ValueError, match="Invalid time range format"):
        parse_time_range_to_timestamps(value, BASE)


def test_split_price_list_returns_matching_sublists_and_indices() -> None:
    """Every sublist has an index list of the same length that points into the list."""
    sublists, indices = split_price_list(PRICES_TODAY, 16, 3)

    assert 0 < len(sublists) <= 3
    assert len(sublists) == len(indices)
    for sublist, idx_list in zip(sublists, indices, strict=True):
        assert len(sublist) == len(idx_list)
        assert [PRICES_TODAY[i] for i in idx_list] == sublist


def test_split_price_list_invalid_input() -> None:
    """Empty list or no sublists yield empty results."""
    assert split_price_list([], 16, 3) == ([], [])
    assert split_price_list(PRICES_TODAY, 16, 0) == ([], [])


def test_group_prices_by_hour_simple_list() -> None:
    """A simple list of 96 quarter-hour prices is grouped into 24 hours."""
    hours = group_prices_by_hour(PRICES_TODAY)
    assert len(hours) == 24
    assert group_prices_by_hour([]) == []


async def test_get_combined_price_list(hass: HomeAssistant) -> None:
    """Tomorrow's prices are only added when tomorrow_valid is set."""
    hass.states.async_set("sensor.src", "1", {"today": [1, 2], "tomorrow": [3, 4]})
    assert get_combined_price_list(hass, "sensor.src") == [1, 2]

    hass.states.async_set(
        "sensor.src", "1", {"today": [1, 2], "tomorrow": [3, 4], "tomorrow_valid": True}
    )
    assert get_combined_price_list(hass, "sensor.src") == [1, 2, 3, 4]

    assert get_combined_price_list(hass, "sensor.missing") == []
    assert get_combined_price_list(hass, "") == []
