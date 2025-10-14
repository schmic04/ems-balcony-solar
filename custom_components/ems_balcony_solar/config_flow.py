"""Adds config flow for EMSBalconySolar."""

from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_create_clientsession

from .api import (
    EMSBalconySolarApiClient,
    EMSBalconySolarApiClientCommunicationError,
    EMSBalconySolarApiClientError,
)
from .const import CONF_NUMBER_1, CONF_NUMBER_2, CONF_SENSOR, DOMAIN, LOGGER


class EMSBalconySolarFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for EMSBalconySolar."""

    VERSION = 1

    async def async_step_user(
        self,
        user_input: dict | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Handle a flow initialized by the user."""
        _errors = {}
        if user_input is not None:
            try:
                await self._test_connection()
                        
            except EMSBalconySolarApiClientCommunicationError as exception:
                LOGGER.error(exception)
                _errors["base"] = "connection"
            except EMSBalconySolarApiClientError as exception:
                LOGGER.exception(exception)
                _errors["base"] = "unknown"
            else:
                if not _errors:
                    # Create a unique ID for this integration instance
                    await self.async_set_unique_id(DOMAIN)
                    self._abort_if_unique_id_configured()
                    return self.async_create_entry(
                        title="EMS Balcony Solar",
                        data=user_input,
                    )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_SENSOR,
                        default=(user_input or {}).get(CONF_SENSOR, vol.UNDEFINED),
                    ): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=self._get_valid_price_sensors(),
                            mode=selector.SelectSelectorMode.DROPDOWN,
                        ),
                    ),
                    vol.Optional(
                        CONF_NUMBER_1,
                        default=(user_input or {}).get(CONF_NUMBER_1, vol.UNDEFINED),
                    ): selector.EntitySelector(
                        selector.EntitySelectorConfig(
                            domain="number",
                        ),
                    ),
                    vol.Optional(
                        CONF_NUMBER_2,
                        default=(user_input or {}).get(CONF_NUMBER_2, vol.UNDEFINED),
                    ): selector.EntitySelector(
                        selector.EntitySelectorConfig(
                            domain="number",
                        ),
                    ),
                },
            ),
            errors=_errors,
        )

    async def _test_connection(self) -> None:
        """Validate connection."""
        client = EMSBalconySolarApiClient(
            session=async_create_clientsession(self.hass),
        )
        await client.async_get_data()

    def _validate_sensor_attributes(self, entity_id: str) -> bool:
        """Validate that the sensor has required attributes.
        
        Args:
            entity_id: The entity ID of the sensor to validate.
            
        Returns:
            True if sensor has all required attributes (today, tomorrow, tomorrow_valid).
        """
        if self.hass is None:
            return False
            
        state = self.hass.states.get(entity_id)
        if state is None:
            return False
            
        # Check for required attributes
        required_attributes = ["today", "tomorrow", "tomorrow_valid"]
        attributes = state.attributes
        
        for attr in required_attributes:
            if attr not in attributes:
                LOGGER.warning(
                    "Sensor %s is missing required attribute: %s",
                    entity_id,
                    attr,
                )
                return False
                
        LOGGER.debug(
            "Sensor %s has all required attributes: %s",
            entity_id,
            required_attributes,
        )
        return True

    def _get_valid_price_sensors(self) -> list[selector.SelectOptionDict]:
        """Get list of sensors that have the required price attributes.
        
        Returns:
            List of sensor options with entity_id as value and friendly name as label.
        """
        if self.hass is None:
            return []
        
        valid_sensors = []
        for state in self.hass.states.async_all("sensor"):
            # Check if sensor has all required attributes
            required_attributes = ["today", "tomorrow", "tomorrow_valid"]
            if all(attr in state.attributes for attr in required_attributes):
                valid_sensors.append(
                    selector.SelectOptionDict(
                        value=state.entity_id,
                        label=state.attributes.get("friendly_name", state.entity_id),
                    )
                )
        
        # Sort by label for better UX
        valid_sensors.sort(key=lambda x: x["label"])
        
        return valid_sensors

    def _get_available_sensors(self) -> list[str]:
        """Get all available sensors in Home Assistant."""
        if self.hass is None:
            return []

        return [state.entity_id for state in self.hass.states.async_all("sensor")]
