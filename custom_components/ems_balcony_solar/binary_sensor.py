"""Binary sensor platform for ems_balcony_solar."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.core import Event, EventStateChangedData, callback
from homeassistant.helpers.event import (
    async_track_state_change_event,
    async_track_time_interval,
)

from .const import UNIQUE_ID_BINARY_SENSOR_PRICE_RANGE_ACTIVE
from .entity import EMSBalconySolarEntity
from .price_list_api import parse_time_range_to_timestamps

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .coordinator import EMSBalconySolarDataUpdateCoordinator
    from .data import EMSBalconySolarConfigEntry

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001
    entry: EMSBalconySolarConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the binary_sensor platform."""
    coordinator = entry.runtime_data.coordinator

    async_add_entities(
        [
            EMSBalconySolarPriceRangeBinarySensor(coordinator, entry),
        ]
    )


class EMSBalconySolarPriceRangeBinarySensor(EMSBalconySolarEntity, BinarySensorEntity):
    """Binary sensor that indicates if current time is in a price sublist range."""

    _attr_device_class = BinarySensorDeviceClass.RUNNING
    _attr_translation_key = "price_range_active"

    def __init__(
        self,
        coordinator: EMSBalconySolarDataUpdateCoordinator,
        config_entry: EMSBalconySolarConfigEntry,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._attr_unique_id = UNIQUE_ID_BINARY_SENSOR_PRICE_RANGE_ACTIVE
        self._attr_name = "Price Range Active"
        self._is_on = False
        self._active_range = None
        self._next_range = None
        self._attr_extra_state_attributes = {
            "active_range": None,
            "next_range": None,
            "last_check": None,
        }
        self._cancel_time_listener = None
        self._cancel_price_listener = None
        self._cancel_switch_listener = None
        self._switch_entity_id = None

    @property
    def is_on(self) -> bool:
        """Return true if current time is in an active price range."""
        return self._is_on

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""
        await super().async_added_to_hass()

        # Update immediately
        self._update_state()

        # Track state changes of the Current Electricity Price sensor
        # This sensor has the price_sublists_time_ranges attribute
        self._cancel_price_listener = async_track_state_change_event(
            self.hass,
            ["sensor.current_electricity_price"],
            self._handle_price_sensor_change,
        )

        # Track state changes of the switch
        # Use wildcard pattern to catch the switch when it becomes available
        potential_switch_id = "switch.ems_balcony_solar"
        self._cancel_switch_listener = async_track_state_change_event(
            self.hass,
            [potential_switch_id],
            self._handle_switch_change,
        )

        # Update every minute
        self._cancel_time_listener = async_track_time_interval(
            self.hass,
            self._handle_time_interval,
            timedelta(minutes=1),
        )

    async def async_will_remove_from_hass(self) -> None:
        """Run when entity will be removed from hass."""
        if self._cancel_time_listener:
            self._cancel_time_listener()
        if self._cancel_price_listener:
            self._cancel_price_listener()
        if self._cancel_switch_listener:
            self._cancel_switch_listener()
        await super().async_will_remove_from_hass()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._update_state()
        self.async_write_ha_state()

    @callback
    def _handle_price_sensor_change(
        self,
        event: Event[EventStateChangedData],  # noqa: ARG002
    ) -> None:
        """Handle price sensor state change."""
        _LOGGER.debug("Price sensor changed, updating price range binary sensor")
        self._update_state()
        self.async_write_ha_state()

    @callback
    def _handle_switch_change(
        self,
        event: Event[EventStateChangedData],  # noqa: ARG002
    ) -> None:
        """Handle switch state change."""
        _LOGGER.debug("Switch changed, updating price range binary sensor")
        self._update_state()
        self.async_write_ha_state()

    @callback
    def _handle_time_interval(self, now: datetime) -> None:  # noqa: ARG002
        """Handle time interval update."""
        self._update_state()
        self.async_write_ha_state()

    def _is_switch_on(self) -> bool:
        """
        Check if the switch is on.

        Dynamically finds the switch entity if not yet set.
        """
        # Try to find switch if not yet found
        if not self._switch_entity_id:
            potential_switch_id = "switch.ems_balcony_solar"
            if self.hass.states.get(potential_switch_id):
                self._switch_entity_id = potential_switch_id
                _LOGGER.debug("Found switch entity: %s", self._switch_entity_id)

        # Check switch state (default to True if not found yet)
        if not self._switch_entity_id:
            return True

        switch_state = self.hass.states.get(self._switch_entity_id)
        return switch_state is not None and switch_state.state == "on"

    def _update_state(self) -> None:
        """Update the state based on current time and price ranges."""
        if not self._is_switch_on():
            self._set_inactive_state()
            return

        time_ranges, reference_date = self._get_time_ranges_and_reference()
        if not time_ranges:
            self._set_inactive_state()
            return

        self._process_time_ranges(time_ranges, reference_date)

    def _set_inactive_state(self) -> None:
        """Set the binary sensor to inactive state with empty attributes."""
        self._is_on = False
        self._active_range = None
        self._next_range = None
        self._attr_extra_state_attributes = {
            "active_range": None,
            "next_range": None,
            "last_check": datetime.now().astimezone().isoformat(),
        }

    def _get_time_ranges_and_reference(self) -> tuple[list, datetime]:
        """Get time ranges and reference date from the price sensor."""
        sensor_entity_id = "sensor.current_electricity_price"
        state = self.hass.states.get(sensor_entity_id)

        if not state or not state.attributes:
            return [], datetime.now().astimezone()

        time_ranges = state.attributes.get("price_sublists_time_ranges", [])
        last_update_str = state.attributes.get("last_update")

        reference_date = self._parse_reference_date(last_update_str)
        return time_ranges, reference_date

    def _parse_reference_date(self, last_update_str: str | None) -> datetime:
        """Parse reference date from last_update string."""
        if last_update_str:
            try:
                return datetime.fromisoformat(last_update_str)
            except ValueError:
                _LOGGER.warning(
                    "Failed to parse last_update timestamp: %s", last_update_str
                )
        return datetime.now().astimezone()

    def _process_time_ranges(self, time_ranges: list, reference_date: datetime) -> None:
        """Process time ranges to determine active and next ranges."""
        now = datetime.now().astimezone()
        all_ranges_with_times = self._parse_all_ranges(time_ranges, reference_date)

        self._is_on = False
        self._active_range = None
        self._next_range = None

        self._find_active_range(all_ranges_with_times, now)
        self._find_next_range(all_ranges_with_times, now)

        self._attr_extra_state_attributes = {
            "active_range": self._active_range,
            "next_range": self._next_range,
            "last_check": now.isoformat(),
        }

        self._log_state_info(now)

    def _parse_all_ranges(self, time_ranges: list, reference_date: datetime) -> list:
        """Parse all time ranges into (range, start, end) tuples."""
        all_ranges_with_times = []
        for sublist_ranges in time_ranges:
            for time_range in sublist_ranges:
                try:
                    start, end = parse_time_range_to_timestamps(
                        time_range, reference_date
                    )
                    all_ranges_with_times.append((time_range, start, end))
                except ValueError as e:
                    _LOGGER.warning("Failed to parse time range %s: %s", time_range, e)
        return all_ranges_with_times

    def _find_active_range(self, all_ranges_with_times: list, now: datetime) -> None:
        """Find if current time is in any active range."""
        for time_range, start, end in all_ranges_with_times:
            if start <= now < end:
                self._is_on = True
                self._active_range = time_range
                break

    def _find_next_range(self, all_ranges_with_times: list, now: datetime) -> None:
        """Find the next upcoming range."""
        next_start_time = None
        for time_range, start, _end in all_ranges_with_times:
            if start > now and (next_start_time is None or start < next_start_time):
                next_start_time = start
                self._next_range = time_range

    def _log_state_info(self, now: datetime) -> None:
        """Log current state information."""
        if self._is_on:
            _LOGGER.debug(
                "Current time %s is in range %s, next range: %s",
                now,
                self._active_range,
                self._next_range,
            )
        else:
            _LOGGER.debug(
                "Current time %s is not in any price range, next range: %s",
                now,
                self._next_range,
            )
