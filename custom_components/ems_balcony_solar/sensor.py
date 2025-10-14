"""Sensor platform for ems_balcony_solar."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.core import Event, EventStateChangedData, callback
from homeassistant.helpers.entity_registry import async_get as async_get_entity_registry
from homeassistant.helpers.event import async_track_state_change_event

from .const import CONF_NUMBER_1, CONF_NUMBER_2, CONF_SENSOR
from .entity import EMSBalconySolarEntity
from .helpers import get_random_value
from .price_list_api import get_combined_price_list

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
    async_add_entities([
        EMSBalconySolarSensor(
            coordinator=entry.runtime_data.coordinator,
            entry=entry,
            source_entity_id=entry.data.get(CONF_SENSOR),
        )
    ])


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
        self._attr_unique_id = f"{entry.entry_id}_sensor"
        self._source_entity_id = source_entity_id
        self._entry = entry
        self._switch_entity_id: str | None = None
        self._number_1_entity_id: str | None = None
        self._number_2_entity_id: str | None = None
        self._unsub_state_change = None
        self._unsub_switch_change = None
        self._unsub_number_1_change = None
        self._unsub_number_2_change = None

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""
        await super().async_added_to_hass()
        
        # Find entity IDs via entity registry
        entity_registry = async_get_entity_registry(self.hass)
        
        # Search for the switch entity
        switch_unique_id = f"{self._entry.entry_id}_ems_balcony_solar"
        for entity_id, entry in entity_registry.entities.items():
            if entry.unique_id == switch_unique_id:
                self._switch_entity_id = entity_id
                break
        
        if not self._switch_entity_id:
            _LOGGER.warning(
                "Could not find switch entity with unique_id: %s",
                switch_unique_id,
            )
        
        # Search for number_1 entity (either selected or created)
        number_1_entity = self._entry.data.get(CONF_NUMBER_1)
        if number_1_entity:
            self._number_1_entity_id = number_1_entity
        else:
            # Look for created number_1
            number_1_unique_id = f"{self._entry.entry_id}_number_1"
            for entity_id, entry in entity_registry.entities.items():
                if entry.unique_id == number_1_unique_id:
                    self._number_1_entity_id = entity_id
                    break
        
        # Search for number_2 entity (either selected or created)
        number_2_entity = self._entry.data.get(CONF_NUMBER_2)
        if number_2_entity:
            self._number_2_entity_id = number_2_entity
        else:
            # Look for created number_2
            number_2_unique_id = f"{self._entry.entry_id}_number_2"
            for entity_id, entry in entity_registry.entities.items():
                if entry.unique_id == number_2_unique_id:
                    self._number_2_entity_id = entity_id
                    break
        
        # Track state changes of the source sensor
        if self._source_entity_id:
            self._unsub_state_change = async_track_state_change_event(
                self.hass,
                [self._source_entity_id],
                self._handle_source_state_change,
            )
        
        # Track state changes of the switch
        if self._switch_entity_id:
            self._unsub_switch_change = async_track_state_change_event(
                self.hass,
                [self._switch_entity_id],
                self._handle_switch_state_change,
            )
        
        # Track state changes of number_1
        if self._number_1_entity_id:
            self._unsub_number_1_change = async_track_state_change_event(
                self.hass,
                [self._number_1_entity_id],
                self._handle_number_state_change,
            )
        
        # Track state changes of number_2
        if self._number_2_entity_id:
            self._unsub_number_2_change = async_track_state_change_event(
                self.hass,
                [self._number_2_entity_id],
                self._handle_number_state_change,
            )
        
        # Perform initial update if switch is on
        if self._is_switch_on():
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
    def _handle_source_state_change(self, event: Event[EventStateChangedData]) -> None:
        """Handle state changes of the source sensor."""
        # Only update if the switch is on
        if self._is_switch_on():
            self._update_sensor("source sensor changed")
    
    @callback
    def _handle_switch_state_change(self, event: Event[EventStateChangedData]) -> None:
        """Handle state changes of the switch."""
        new_state = event.data.get("new_state")
        
        # If switch was turned on, update the sensor
        if new_state and new_state.state == "on":
            self._update_sensor("switch turned on")
    
    @callback
    def _handle_number_state_change(self, event: Event[EventStateChangedData]) -> None:
        """Handle state changes of number entities."""
        # Only update if the switch is on
        if self._is_switch_on():
            self._update_sensor("number entity changed")
    
    def _update_sensor(self, reason: str) -> None:
        """Update the sensor and log the reason."""
        _LOGGER.info("Sensor updated (%s)", reason)
        self.async_write_ha_state()
    
    def _is_switch_on(self) -> bool:
        """Check if the switch is on."""
        if not self._switch_entity_id:
            return False
        switch_state = self.hass.states.get(self._switch_entity_id)
        return switch_state is not None and switch_state.state == "on"

    @property
    def native_value(self) -> float | None:
        """Return the native value of the sensor."""
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
        
        if self._source_entity_id:
            # Get combined price list from the source sensor
            price_list = get_combined_price_list(self.hass, self._source_entity_id)
            attributes["price_list"] = price_list
            attributes["price_list_count"] = len(price_list)
        else:
            attributes["price_list"] = []
            attributes["price_list_count"] = 0
        
        return attributes


