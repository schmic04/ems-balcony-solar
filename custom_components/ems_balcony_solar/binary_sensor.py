"""EMS Balcony Solar binary sensor platform."""

from __future__ import annotations
from datetime import datetime
import logging

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event, async_track_time_change
from homeassistant.util import dt as dt_util

from .const import DOMAIN, CONF_NORDPOOL_SENSOR, CONF_HOURS_OF_OPERATING, DEFAULT_HOURS_OF_OPERATING

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up EMS Balcony Solar binary sensors from a config entry."""
    nordpool_sensor = entry.data[CONF_NORDPOOL_SENSOR]
    hours_of_operating_sensor = entry.data[CONF_HOURS_OF_OPERATING]

    sensors = [
        EmsBalconySolarCurrentHourBinarySensor(nordpool_sensor, hours_of_operating_sensor),
    ]

    async_add_entities(sensors)


class EmsBalconySolarCurrentHourBinarySensor(BinarySensorEntity):
    """Binary sensor that indicates if current hour is in optimal sublists."""

    _attr_has_entity_name = True

    def __init__(self, nordpool_sensor: str, hours_of_operating_sensor: str) -> None:
        """Initialize the binary sensor."""
        self._nordpool_sensor = nordpool_sensor
        self._hours_of_operating_sensor = hours_of_operating_sensor
        self._attr_name = "Current Hour Optimal"
        self._attr_unique_id = f"{nordpool_sensor}_current_hour_optimal"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, nordpool_sensor)},
            name="EMS Balcony Solar",
            manufacturer="EMS",
            model="Balcony Solar",
        )
        self._unsubscribe_callbacks: list = []

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

    def _get_num_price_sublists_sensor(self) -> str:
        """Get the entity ID for the num_price_sublists sensor created by this integration."""
        return "sensor.ems_balcony_solar_number_price_sublists"

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""
        await super().async_added_to_hass()

        # Get the num_price_sublists sensor ID
        num_sublists_sensor_id = self._get_num_price_sublists_sensor()

        # Track state changes of the num_price_sublists sensor and hours_of_operating sensor
        self._unsubscribe_callbacks.append(
            async_track_state_change_event(
                self.hass,
                [num_sublists_sensor_id, self._hours_of_operating_sensor],
                self._handle_sensor_state_change,
            )
        )

        # Track time changes to update when hour changes
        self._unsubscribe_callbacks.append(
            async_track_time_change(
                self.hass,
                self._handle_time_change,
                minute=0,
                second=0,
            )
        )

        await self._update_state()

    async def async_will_remove_from_hass(self) -> None:
        """Run when entity will be removed from hass."""
        for unsubscribe in self._unsubscribe_callbacks:
            if unsubscribe:
                unsubscribe()

    @callback
    def _handle_sensor_state_change(self, event: Event) -> None:
        """Handle state changes of the input sensors."""
        self.hass.async_create_task(self._update_state())

    @callback
    def _handle_time_change(self, now: datetime) -> None:
        """Handle time changes."""
        self.hass.async_create_task(self._update_state())

    def _get_current_hour_index(self) -> int:
        """Get the current hour as index in Home Assistant timezone."""
        # Use Home Assistant's default timezone-aware current time
        now = dt_util.now()
        return now.hour

    async def _update_state(self) -> None:
        """Update the binary sensor state."""
        # Get the num_price_sublists sensor state
        num_sublists_sensor_id = self._get_num_price_sublists_sensor()
        num_sublists_state = self.hass.states.get(num_sublists_sensor_id)

        if not num_sublists_state or num_sublists_state.state in (
            STATE_UNAVAILABLE,
            STATE_UNKNOWN,
        ):
            self._attr_is_on = False
            self._attr_extra_state_attributes = {
                "current_hour": self._get_current_hour_index(),
                "optimal_indices": [],
                "hours_of_operating_setting": self._get_hours_of_operating_value(),
                "error": "num_price_sublists sensor unavailable",
                "num_sublists_sensor": num_sublists_sensor_id,
            }
            self.async_write_ha_state()
            return

        try:
            # Get attributes from the num_price_sublists sensor
            sublist_sums = num_sublists_state.attributes.get("sublist_sums", [])
            index_lists = num_sublists_state.attributes.get("index_lists", [])

            if not sublist_sums or not index_lists:
                self._attr_is_on = False
                self._attr_extra_state_attributes = {
                    "current_hour": self._get_current_hour_index(),
                    "optimal_indices": [],
                    "hours_of_operating_setting": self._get_hours_of_operating_value(),
                    "error": "no sublist data available",
                    "num_sublists_sensor": num_sublists_sensor_id,
                }
                self.async_write_ha_state()
                return

            # Create list of (sum, index_list) pairs and sort by sum (descending for highest prices)
            sum_index_pairs = list(zip(sublist_sums, index_lists))
            sum_index_pairs.sort(key=lambda x: x[0], reverse=True)

            # Select sublists based on total duration not exceeding hours_of_operating
            hours_of_operating = self._get_hours_of_operating_value()
            best_sublists = []
            total_duration = 0
            
            for sum_value, index_list in sum_index_pairs:
                sublist_duration = len(index_list)
                
                # If adding this sublist would exceed the limit, check if we should still add it
                if total_duration + sublist_duration > hours_of_operating:
                    # If we haven't selected any sublists yet, or if this would be the first to exceed,
                    # add it anyway as specified in requirements
                    if not best_sublists or total_duration < hours_of_operating:
                        best_sublists.append((sum_value, index_list))
                        total_duration += sublist_duration
                    break
                else:
                    # Safe to add without exceeding limit
                    best_sublists.append((sum_value, index_list))
                    total_duration += sublist_duration
                    
                    # If we've reached the exact target, stop
                    if total_duration >= hours_of_operating:
                        break

            # Get all indices from the selected sublists
            optimal_indices = []
            for _, index_list in best_sublists:
                optimal_indices.extend(index_list)

            # Remove duplicates and sort
            optimal_indices = sorted(set(optimal_indices))

            # Check if current hour is in optimal indices
            current_hour = self._get_current_hour_index()
            self._attr_is_on = current_hour in optimal_indices

            self._attr_extra_state_attributes = {
                "current_hour": current_hour,
                "optimal_indices": optimal_indices,
                "hours_of_operating_setting": hours_of_operating,
                "total_duration": total_duration,
                "best_sublist_sums": [pair[0] for pair in best_sublists],
                "best_sublist_indices": [pair[1] for pair in best_sublists],
                "best_sublist_durations": [len(pair[1]) for pair in best_sublists],
                "selected_sublists_count": len(best_sublists),
                "total_sublists_available": len(sublist_sums),
                "num_sublists_sensor": num_sublists_sensor_id,
                "hours_of_operating_sensor": self._hours_of_operating_sensor,
            }

        except (ValueError, TypeError, KeyError) as exc:
            self._attr_is_on = False
            self._attr_extra_state_attributes = {
                "current_hour": self._get_current_hour_index(),
                "optimal_indices": [],
                "hours_of_operating_setting": self._get_hours_of_operating_value(),
                "error": f"Error processing data: {exc!s}",
                "num_sublists_sensor": num_sublists_sensor_id,
            }
            _LOGGER.debug("Error processing binary sensor data: %s", exc)

        self.async_write_ha_state()

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        num_sublists_sensor_id = self._get_num_price_sublists_sensor()
        num_sublists_state = self.hass.states.get(num_sublists_sensor_id)

        return (
            num_sublists_state is not None
            and num_sublists_state.state not in (STATE_UNAVAILABLE, STATE_UNKNOWN)
        )

    @property
    def is_on(self) -> bool | None:
        """Return true if current hour is in optimal time windows."""
        return self._attr_is_on
