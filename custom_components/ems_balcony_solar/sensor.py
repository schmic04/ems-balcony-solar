"""EMS Balcony Solar sensor platform."""

from __future__ import annotations
import logging

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event

from .const import (
    DOMAIN,
    CONF_NORDPOOL_SENSOR,
    CONF_WINDOW_SENSOR,
    CONF_HOURS_OF_OPERATING,
    DEFAULT_WINDOW,
    DEFAULT_HOURS_OF_OPERATING,
)
from .ems_tools import dynamic_sublists_with_window

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up EMS Balcony Solar sensors from a config entry."""
    nordpool_sensor = entry.data[CONF_NORDPOOL_SENSOR]
    window_sensor = entry.data[CONF_WINDOW_SENSOR]
    hours_of_operating_sensor = entry.data[CONF_HOURS_OF_OPERATING]

    sensors = [
        EmsBalconySolarSensor(
            nordpool_sensor, window_sensor, hours_of_operating_sensor, "price_avg", "Price Average"
        ),
        EmsBalconySolarSensor(
            nordpool_sensor, window_sensor, hours_of_operating_sensor, "price_list_length", "Price List Length"
        ),
        EmsBalconySolarSensor(
            nordpool_sensor,
            window_sensor,
            hours_of_operating_sensor,
            "num_price_sublists",
            "Number Price Sublists",
        ),
    ]

    async_add_entities(sensors)


class EmsBalconySolarSensor(SensorEntity):
    """Representation of an EMS Balcony Solar sensor."""

    _attr_has_entity_name = True

    def __init__(
        self, 
        nordpool_sensor: str, 
        window_sensor: str, 
        hours_of_operating_sensor: str,
        sensor_type: str, 
        name: str
    ) -> None:
        """Initialize the sensor."""
        self._nordpool_sensor = nordpool_sensor
        self._window_sensor = window_sensor
        self._hours_of_operating_sensor = hours_of_operating_sensor
        self._sensor_type = sensor_type
        self._attr_name = name
        self._attr_unique_id = f"{nordpool_sensor}_{sensor_type}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, nordpool_sensor)},
            name="EMS Balcony Solar",
            manufacturer="EMS",
            model="Balcony Solar",
        )
        self._unsubscribe_callback = None

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""
        await super().async_added_to_hass()

        # Track nordpool, window and hours of operating sensor changes
        self._unsubscribe_callback = async_track_state_change_event(
            self.hass,
            [self._nordpool_sensor, self._window_sensor, self._hours_of_operating_sensor],
            self._handle_sensor_state_change,
        )

        await self._update_from_sensors()

    async def async_will_remove_from_hass(self) -> None:
        """Run when entity will be removed from hass."""
        if self._unsubscribe_callback:
            self._unsubscribe_callback()

    @callback
    def _handle_sensor_state_change(self, event: Event) -> None:
        """Handle state changes of the input sensors."""
        self.hass.async_create_task(self._update_from_sensors())

    def _get_window_value(self) -> int:
        """Get the window value from window sensor or default."""
        window_state = self.hass.states.get(self._window_sensor)
        
        if not window_state or window_state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            return DEFAULT_WINDOW
            
        try:
            window_value = int(float(window_state.state))
            return max(1, window_value)
        except (ValueError, TypeError):
            _LOGGER.debug("Invalid window sensor value: %s", window_state.state)
            return DEFAULT_WINDOW

    def _get_hours_of_operating_value(self) -> int:
        """Get the hours of operating value from sensor or default."""
        hours_state = self.hass.states.get(self._hours_of_operating_sensor)
        
        if not hours_state or hours_state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            return DEFAULT_HOURS_OF_OPERATING
            
        try:
            hours_value = int(float(hours_state.state))
            return max(1, hours_value)
        except (ValueError, TypeError):
            _LOGGER.debug("Invalid hours of operating sensor value: %s", hours_state.state)
            return DEFAULT_HOURS_OF_OPERATING

    async def _update_from_sensors(self) -> None:
        """Update sensor value based on input sensor data."""
        nordpool_state = self.hass.states.get(self._nordpool_sensor)

        if not nordpool_state or nordpool_state.state in (
            STATE_UNAVAILABLE,
            STATE_UNKNOWN,
        ):
            self._attr_native_value = None
            self._attr_extra_state_attributes = {}
            self.async_write_ha_state()
            return

        try:
            today_prices = nordpool_state.attributes.get("today", [])
            tomorrow_prices = nordpool_state.attributes.get("tomorrow", [])
            tomorrow_valid = nordpool_state.attributes.get("tomorrow_valid", False)

            if tomorrow_valid and tomorrow_prices:
                nordpool_prices = today_prices + tomorrow_prices
            else:
                nordpool_prices = today_prices

            if not nordpool_prices:
                self._attr_native_value = None
                self._attr_extra_state_attributes = {}
                self.async_write_ha_state()
                return

            window_value = self._get_window_value()
            hours_of_operating_value = self._get_hours_of_operating_value()

            match self._sensor_type:
                case "price_avg":
                    self._attr_native_value = sum(nordpool_prices) / len(
                        nordpool_prices
                    )
                    self._attr_unit_of_measurement = nordpool_state.attributes.get(
                        "unit", "€/kWh"
                    )
                    self._attr_extra_state_attributes = {
                        "today_count": len(today_prices),
                        "tomorrow_count": len(tomorrow_prices) if tomorrow_valid else 0,
                        "tomorrow_valid": tomorrow_valid,
                        "window_value": window_value,
                        "hours_of_operating": hours_of_operating_value,
                        "window_sensor": self._window_sensor,
                        "hours_of_operating_sensor": self._hours_of_operating_sensor,
                    }

                case "price_list_length":
                    self._attr_native_value = len(nordpool_prices)
                    self._attr_unit_of_measurement = None
                    self._attr_extra_state_attributes = {
                        "price_list": nordpool_prices,
                        "count": len(nordpool_prices),
                        "today_prices": today_prices,
                        "tomorrow_prices": tomorrow_prices if tomorrow_valid else [],
                        "today_count": len(today_prices),
                        "tomorrow_count": len(tomorrow_prices) if tomorrow_valid else 0,
                        "tomorrow_valid": tomorrow_valid,
                        "window_value": window_value,
                        "hours_of_operating": hours_of_operating_value,
                        "window_sensor": self._window_sensor,
                        "hours_of_operating_sensor": self._hours_of_operating_sensor,
                    }

                case "num_price_sublists":
                    sublists, index_lists = dynamic_sublists_with_window(
                        nordpool_prices, window=window_value
                    )
                    sublist_sums = [sum(sublist) for sublist in sublists]
                    sublist_avgs = [
                        (sum(sublist) / len(sublist)) for sublist in sublists
                    ]
                    sublist_lengths = [len(sublist) for sublist in sublists]

                    self._attr_native_value = len(sublists)
                    self._attr_unit_of_measurement = None
                    self._attr_extra_state_attributes = {
                        "sublists": sublists,
                        "sublist_sums": sublist_sums,
                        "sublist_avgs": sublist_avgs,
                        "sublist_lengths": sublist_lengths,
                        "index_lists": index_lists,
                        "sublist_count": len(sublists),
                        "nordpool_prices": nordpool_prices,
                        "nordpool_prices_length": len(nordpool_prices),
                        "window_value": window_value,
                        "hours_of_operating": hours_of_operating_value,
                        "window_sensor": self._window_sensor,
                        "hours_of_operating_sensor": self._hours_of_operating_sensor,
                    }

        except (ValueError, TypeError, KeyError) as exc:
            self._attr_native_value = None
            self._attr_extra_state_attributes = {}
            _LOGGER.debug("Error processing sensor data: %s", exc)

        self.async_write_ha_state()

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        nordpool_state = self.hass.states.get(self._nordpool_sensor)

        return (
            nordpool_state is not None
            and nordpool_state.state not in (STATE_UNAVAILABLE, STATE_UNKNOWN)
        )

    @property
    def native_value(self) -> float | str | None:
        """Return the state of the sensor."""
        return self._attr_native_value
