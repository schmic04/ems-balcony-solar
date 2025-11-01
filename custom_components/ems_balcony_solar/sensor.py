"""Sensor platform for ems_balcony_solar."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.core import Event, EventStateChangedData, callback
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.util import dt as dt_util

from .const import (
    CONF_NUMBER_OF_SUBLISTS,
    CONF_SENSOR,
    CONF_SUBLIST_LENGTH,
    UNIQUE_ID_SENSOR_CURRENT_ELECTRICITY_PRICE,
)
from .entity import EMSBalconySolarEntity
from .helpers import get_random_value
from .price_list_api import (
    convert_indices_to_time_ranges,
    get_combined_price_list,
    group_prices_by_hour,
    split_price_list,
)

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
    """Set up the sensor platform."""
    # Always create the sensor
    async_add_entities(
        [
            EMSBalconySolarSensor(
                coordinator=entry.runtime_data.coordinator,
                entry=entry,
                source_entity_id=entry.data.get(CONF_SENSOR),
            )
        ]
    )


class EMSBalconySolarSensor(EMSBalconySolarEntity, SensorEntity):
    """EMS Balcony Solar Sensor class."""

    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "€ct/kWh"
    _attr_icon = "mdi:currency-eur"

    def __init__(
        self,
        coordinator: EMSBalconySolarDataUpdateCoordinator,
        entry: EMSBalconySolarConfigEntry,
        source_entity_id: str | None,
    ) -> None:
        """Initialize the sensor class."""
        super().__init__(coordinator)
        self._attr_name = "Current Electricity Price"
        self._attr_unique_id = UNIQUE_ID_SENSOR_CURRENT_ELECTRICITY_PRICE
        self._source_entity_id = source_entity_id
        self._entry = entry
        self._switch_entity_id: str | None = None
        self._debugging_switch_entity_id: str | None = None
        self._sublist_length_entity_id: str | None = None
        self._number_of_sublists_entity_id: str | None = None
        self._unsub_state_change = None
        self._unsub_switch_change = None
        self._unsub_sublist_length_change = None
        self._unsub_number_of_sublists_change = None

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""
        await super().async_added_to_hass()

        # Use predictable entity IDs instead of searching entity registry
        # This avoids blocking during initialization

        # Debugging switch will be found dynamically if needed
        self._debugging_switch_entity_id = "switch.debugging"

        # Try to get number entities from config, otherwise use predictable IDs
        sublist_length_entity = self._entry.data.get(CONF_SUBLIST_LENGTH)
        if sublist_length_entity:
            self._sublist_length_entity_id = sublist_length_entity
        else:
            # Use predictable entity_id
            self._sublist_length_entity_id = "number.sublist_length"

        number_of_sublists_entity = self._entry.data.get(CONF_NUMBER_OF_SUBLISTS)
        if number_of_sublists_entity:
            self._number_of_sublists_entity_id = number_of_sublists_entity
        else:
            # Use predictable entity_id
            self._number_of_sublists_entity_id = "number.number_of_sublists"

        # Track state changes of the source sensor
        if self._source_entity_id:
            self._unsub_state_change = async_track_state_change_event(
                self.hass,
                [self._source_entity_id],
                self._handle_source_state_change,
            )

        # Track state changes of the switch (use common entity_id pattern)
        potential_switch_id = "switch.ems_balcony_solar"
        self._unsub_switch_change = async_track_state_change_event(
            self.hass,
            [potential_switch_id],
            self._handle_switch_state_change,
        )

        # Track state changes of sublist_length
        if self._sublist_length_entity_id:
            self._unsub_sublist_length_change = async_track_state_change_event(
                self.hass,
                [self._sublist_length_entity_id],
                self._handle_number_state_change,
            )

        # Track state changes of number_of_sublists
        if self._number_of_sublists_entity_id:
            self._unsub_number_of_sublists_change = async_track_state_change_event(
                self.hass,
                [self._number_of_sublists_entity_id],
                self._handle_number_state_change,
            )

        # Perform initial update
        # Note: Don't check switch state here to avoid blocking during initialization
        # The switch check will happen in the property getters
        self._update_sensor("initial setup")

    async def async_will_remove_from_hass(self) -> None:
        """Run when entity will be removed from hass."""
        await super().async_will_remove_from_hass()

        # Unsubscribe from state changes
        if self._unsub_state_change:
            self._unsub_state_change()
            self._unsub_state_change = None

        if self._unsub_switch_change:
            self._unsub_switch_change()
            self._unsub_switch_change = None

        if self._unsub_number_1_change:
            self._unsub_number_1_change()
            self._unsub_number_1_change = None

        if self._unsub_number_2_change:
            self._unsub_number_2_change()
            self._unsub_number_2_change = None

    @callback
    def _handle_source_state_change(self, _event: Event[EventStateChangedData]) -> None:
        """Handle state changes of the source sensor."""
        # Only update if the switch is on
        if self._is_switch_on():
            self._update_sensor("source sensor changed")

    @callback
    def _handle_switch_state_change(self, event: Event[EventStateChangedData]) -> None:
        """Handle state changes of the switch."""
        new_state = event.data.get("new_state")

        # Update sensor whenever switch state changes (on or off)
        if new_state:
            if new_state.state == "on":
                self._update_sensor("switch turned on")
            else:
                self._update_sensor("switch turned off")

    @callback
    def _handle_number_state_change(self, _event: Event[EventStateChangedData]) -> None:
        """Handle state changes of number entities."""
        # Only update if the switch is on
        if self._is_switch_on():
            self._update_sensor("number entity changed")

    def _update_sensor(self, reason: str) -> None:
        """Update the sensor and log the reason."""
        _LOGGER.info("Sensor updated (%s)", reason)
        self.async_write_ha_state()

    def _is_switch_on(self) -> bool:
        """
        Check if the switch is on.

        Dynamically finds the switch entity if not yet set.
        """
        # Try to find switch if not yet found
        if not self._switch_entity_id:
            # Simple approach: Try common entity_id pattern
            potential_id = "switch.ems_balcony_solar"
            if self.hass.states.get(potential_id):
                self._switch_entity_id = potential_id
                _LOGGER.debug("Found switch entity: %s", self._switch_entity_id)

        # Check switch state (default to True if not found yet)
        if not self._switch_entity_id:
            return True

        switch_state = self.hass.states.get(self._switch_entity_id)
        return switch_state is not None and switch_state.state == "on"

    @property
    def is_debugging(self) -> bool:
        """Check if debugging is enabled."""
        if not self._debugging_switch_entity_id:
            return False
        debugging_state = self.hass.states.get(self._debugging_switch_entity_id)
        return debugging_state is not None and debugging_state.state == "on"

    @property
    def native_value(self) -> float | None:
        """Return the native value of the sensor."""
        # If switch is off, return None
        if not self._is_switch_on():
            return None

        if self._source_entity_id:
            # Get the value from the source sensor
            state = self.hass.states.get(self._source_entity_id)
            if state and state.state not in ("unknown", "unavailable"):
                try:
                    return float(state.state)
                except (ValueError, TypeError):
                    return None
            return None
        # Return random value if no source sensor is configured
        return get_random_value()

    @property
    def extra_state_attributes(self) -> dict[str, list | int]:
        """Return the state attributes."""
        attributes = {}

        # Add last_update timestamp for reference_date calculation
        attributes["last_update"] = dt_util.now().isoformat()

        # If switch is off, return empty/default attributes
        if not self._is_switch_on():
            attributes["price_list"] = []
            attributes["price_list_count"] = 0
            attributes["price_sublists"] = []
            attributes["price_sublists_count"] = 0
            attributes["price_sublists_indices"] = []
            attributes["price_sublists_time_ranges"] = []
            attributes["hourly_prices"] = []
            attributes["hourly_prices_count"] = 0
            return attributes

        if self._source_entity_id:
            # Get combined price list from the source sensor
            price_list = get_combined_price_list(self.hass, self._source_entity_id)
            attributes["price_list"] = price_list
            attributes["price_list_count"] = len(price_list)

            # Split price list into sublists
            sublist_length = self._get_number_value(self._sublist_length_entity_id)
            number_of_sublists = self._get_number_value(
                self._number_of_sublists_entity_id
            )

            if sublist_length and number_of_sublists:
                sublists, indices = split_price_list(
                    price_list, int(sublist_length), int(number_of_sublists)
                )
                attributes["price_sublists"] = sublists
                attributes["price_sublists_count"] = len(sublists)
                attributes["price_sublists_indices"] = indices
                # Convert indices to time ranges
                time_ranges = convert_indices_to_time_ranges(indices)
                attributes["price_sublists_time_ranges"] = time_ranges
                # Group prices by hour for easier hour-based access
                hourly_prices = group_prices_by_hour(price_list)
                attributes["hourly_prices"] = hourly_prices
                attributes["hourly_prices_count"] = len(hourly_prices)

            else:
                attributes["price_sublists"] = []
                attributes["price_sublists_count"] = 0
                attributes["price_sublists_indices"] = []
                attributes["price_sublists_time_ranges"] = []
                attributes["hourly_prices"] = []
                attributes["hourly_prices_count"] = 0
        else:
            attributes["price_list"] = []
            attributes["price_list_count"] = 0
            attributes["price_sublists"] = []
            attributes["price_sublists_count"] = 0
            attributes["price_sublists_indices"] = []
            attributes["price_sublists_time_ranges"] = []
            attributes["hourly_prices"] = []
            attributes["hourly_prices_count"] = 0

        return attributes

    def _get_number_value(self, entity_id: str | None) -> float | None:
        """Get the value from a number entity."""
        if not entity_id:
            return None
        state = self.hass.states.get(entity_id)
        if state and state.state not in ("unknown", "unavailable"):
            try:
                return float(state.state)
            except (ValueError, TypeError):
                return None
        return None
